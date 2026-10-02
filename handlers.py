import asyncio
import html
import logging
import os
import time
from typing import Dict, List

import aiohttp
from aiogram import BaseMiddleware, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from init import (ALERT_HTTP_TIMEOUT, ALERT_POLL_SECONDS, ALERT_WATCHDOG_FAILURES, ALLOWED_IDS,
                  AM_ALERTS_URL, AM_TOKEN, DB_PATH, PROM_QUERY_URL, PROM_TOKEN, bot)
from sql import DatabaseManager

router = Router()
db = DatabaseManager(DB_PATH)
log = logging.getLogger(__name__)

# Node names as used in Prometheus' "server" label — match your own scrape config.
SERVERS_ORDER = [s for s in os.environ.get("SERVERS_ORDER", "srv1,srv2,srv3").split(",") if s]


class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        u = getattr(event, "from_user", None) or data.get("event_from_user")
        if u is None or u.id in ALLOWED_IDS:
            return await handler(event, data)
        return None  # silently ignore everyone else


router.message.outer_middleware(AccessMiddleware())


# ======================================================================
#  small helpers
# ======================================================================
def fmt_uptime(sec: float) -> str:
    sec = int(max(0, sec))
    d, rem = divmod(sec, 86400)
    h = rem // 3600
    return f"{d}д {h}ч" if d else f"{h}ч"


def settings_block(row) -> str:
    _, _u, alerts_on = row
    firing = len(db.list_firing_fingerprints())
    out = f"Алерты: {'включены' if alerts_on else 'выключены'}"
    if firing:
        out += f"\nСейчас активных алертов: <b>{firing}</b>"
    return out


# ======================================================================
#  commands
# ======================================================================
@router.message(Command("start"))
async def cmd_start(msg: Message):
    uid = msg.from_user.id
    db.add_user(uid, msg.from_user.username or msg.from_user.first_name or str(uid))
    row = db.get_user_info(uid)
    await msg.answer(
        "<b>Мониторинг инфраструктуры</b>\n\n"
        "• сразу сообщает о проблемах и о возврате в норму (алерты);\n"
        "• по запросу отдаёт состояние серверов, сервисов и сертификатов.\n\n"
        + settings_block(row) + "\n\n"
        "Команды — в меню слева от поля ввода, или /help."
    )


@router.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "<b>Команды</b>\n\n"
        "<b>Сводки</b>\n"
        "/servers — CPU, RAM, диск, аптайм по узлам\n"
        "/services — что работает и что нет\n"
        "/certs — сколько дней осталось у TLS-сертификатов\n"
        "/alerts — активные алерты сейчас\n\n"
        "<b>Настройки</b>\n"
        "/status — что включено\n"
        "/alerts on | off — подписка на алерты"
    )


@router.message(Command("status"))
async def cmd_status(msg: Message):
    row = db.get_user_info(msg.from_user.id)
    if not row:
        await msg.answer("Нажми /start.")
        return
    await msg.answer("<b>Настройки</b>\n\n" + settings_block(row))


@router.message(Command("alerts"))
async def cmd_alerts(msg: Message, command: CommandObject):
    uid = msg.from_user.id
    if not db.get_user_info(uid):
        db.add_user(uid, msg.from_user.username or str(uid))
    arg = (command.args or "").strip().lower()
    if arg in ("on", "вкл"):
        db.set_alerts(uid, True)
        await msg.answer("Алерты включены.")
        return
    if arg in ("off", "выкл"):
        db.set_alerts(uid, False)
        await msg.answer("Алерты выключены.")
        return
    await msg.answer(await render_active_alerts())


@router.message(Command("servers"))
async def cmd_servers(msg: Message):
    await msg.answer(await render_servers())


@router.message(Command("services"))
async def cmd_services(msg: Message):
    await msg.answer(await render_services())


@router.message(Command("certs"))
async def cmd_certs(msg: Message):
    await msg.answer(await render_certs())


# ======================================================================
#  Prometheus
# ======================================================================
def _auth(token: str) -> dict:
    """Token goes in the Authorization header, not in the URL (URLs end up in proxy logs)."""
    return {"Authorization": f"Bearer {token}"}


async def _promq(session: aiohttp.ClientSession, query: str) -> List[dict]:
    async with session.get(PROM_QUERY_URL, params={"query": query},
                           headers=_auth(PROM_TOKEN),
                           timeout=aiohttp.ClientTimeout(total=ALERT_HTTP_TIMEOUT)) as r:
        r.raise_for_status()
        j = await r.json()
    if j.get("status") != "success":
        raise RuntimeError(j.get("error", "prometheus error"))
    return j["data"]["result"]


def _by_server(result: List[dict]) -> Dict[str, float]:
    out = {}
    for s in result:
        srv = s["metric"].get("server")
        if srv:
            try:
                out[srv] = float(s["value"][1])
            except (ValueError, TypeError):
                pass
    return out


async def render_servers() -> str:
    q = {
        "cpu":  '100 - (avg by (server) (rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)',
        "ram":  '(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100',
        "disk": '(1 - avg by (server)(node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay|squashfs"}) '
                '/ avg by (server)(node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay|squashfs"})) * 100',
        "load": 'node_load1',
        "up":   'up{job=~"node_.*"}',
        "boot": 'node_boot_time_seconds',
        "swap": '(node_memory_SwapTotal_bytes > bool 0) * (1 - node_memory_SwapFree_bytes / (node_memory_SwapTotal_bytes > 0)) * 100',
        # real hwmon sensors only (chip=~"pci.*") — excludes bogus acpitz/thermal_zone
        # readings some laptops-as-servers report as a stuck fake value
        "temp": 'max by (server) (node_hwmon_temp_celsius{chip=~"pci.*"})',
    }
    try:
        async with aiohttp.ClientSession() as s:
            res = {k: _by_server(await _promq(s, v)) for k, v in q.items()}
    except Exception as e:
        return f"Не удалось получить метрики: {e}"

    now = time.time()
    out = ["<b>Серверы</b>"]
    for srv in SERVERS_ORDER:
        if srv not in res["up"]:
            out.append(f"\n<b>{srv.upper()}</b> — нет данных")
            continue
        alive = res["up"].get(srv, 0) >= 1
        cpu, ram = res["cpu"].get(srv), res["ram"].get(srv)
        disk, swap = res["disk"].get(srv), res["swap"].get(srv, 0.0)
        load = res["load"].get(srv)
        temp = res["temp"].get(srv)
        up = fmt_uptime(now - res["boot"][srv]) if srv in res["boot"] else "?"

        def g(x):
            return f"{x:.0f}%" if isinstance(x, (int, float)) else "?"

        warn = []
        if isinstance(disk, float) and disk >= 85:
            warn.append("диск")
        if isinstance(ram, float) and ram >= 90:
            warn.append("память")
        if isinstance(swap, float) and swap >= 60:
            warn.append("swap")
        if isinstance(temp, float) and temp >= 85:
            warn.append("температура")
        head = f"\n<b>{srv.upper()}</b>"
        if not alive:
            head += " · НЕ ОТВЕЧАЕТ"
        elif warn:
            head += " · ⚠ " + ", ".join(warn)
        out.append(head)
        line = f"CPU {g(cpu)} · RAM {g(ram)} · диск {g(disk)} · swap {g(swap)}"
        if isinstance(temp, float):
            line += f" · temp {temp:.0f}°C"
        out.append(line)
        out.append(f"load {load:.2f} · аптайм {up}" if isinstance(load, float)
                   else f"аптайм {up}")
    return "\n".join(out)


async def render_services() -> str:
    try:
        async with aiohttp.ClientSession() as s:
            res = await _promq(s, "up")
    except Exception as e:
        return f"Не удалось получить статус сервисов: {e}"
    total = len(res)
    down = [(m["metric"].get("job", "?"), m["metric"].get("instance", "?"))
            for m in res if m["value"][1] != "1"]
    if not down:
        return f"<b>Сервисы</b>\n\nВсе {total} в норме."
    lines = [f"<b>Сервисы</b>\n\n{total - len(down)}/{total} в норме. Не отвечают:"]
    for job, inst in sorted(down):
        lines.append(f"• {html.escape(job)} — {html.escape(inst)}")
    return "\n".join(lines)


async def render_certs() -> str:
    try:
        async with aiohttp.ClientSession() as s:
            res = await _promq(s, "(probe_ssl_earliest_cert_expiry - time()) / 86400")
    except Exception as e:
        return f"Не удалось получить данные по сертификатам: {e}"
    rows = []
    for m in res:
        try:
            days = float(m["value"][1])
        except (ValueError, TypeError):
            continue
        host = m["metric"].get("instance", "?").replace("https://", "").split("/")[0]
        rows.append((days, host))
    if not rows:
        return "Данных по сертификатам нет."
    rows.sort()
    soon = [f"{h} — {d:.0f} дн" for d, h in rows if d < 14]
    body = "\n".join(f"{d:>4.0f}  {h}" for d, h in rows)
    head = "<b>TLS-сертификаты</b>"
    if soon:
        head += "\n⚠ скоро истекают: " + "; ".join(soon)
    return head + f"\n<pre>{body}</pre>"


# ======================================================================
#  Alertmanager
# ======================================================================
def _sev(labels): return labels.get("severity", "").lower()
def _where(labels): return labels.get("server") or labels.get("instance") or labels.get("job") or ""


def _fmt_firing(a: dict) -> str:
    lb, an = a.get("labels", {}), a.get("annotations", {})
    name = html.escape(lb.get("alertname", "alert"))
    sub = " · ".join(x for x in (_sev(lb), html.escape(_where(lb))) if x)
    summ = html.escape(an.get("summary") or an.get("description") or "")
    text = f"<b>Проблема · {name}</b>"
    if sub:
        text += f"\n{sub}"
    if summ:
        text += f"\n{summ}"
    return text


def _fmt_resolved(name: str) -> str:
    return f"<b>В норме · {html.escape(name)}</b>"


async def _fetch_alerts(session: aiohttp.ClientSession) -> List[dict]:
    params = {"active": "true", "silenced": "false", "inhibited": "false"}
    async with session.get(AM_ALERTS_URL, params=params, headers=_auth(AM_TOKEN),
                           timeout=aiohttp.ClientTimeout(total=ALERT_HTTP_TIMEOUT)) as r:
        r.raise_for_status()
        return await r.json()


async def _broadcast(text: str):
    for uid in db.get_alert_users():
        try:
            await bot.send_message(uid, text)
        except Exception as e:
            log.error("alert to %s failed: %s", uid, e)


async def render_active_alerts() -> str:
    try:
        async with aiohttp.ClientSession() as s:
            data = await _fetch_alerts(s)
    except Exception as e:
        return f"Не удалось получить алерты: {e}"
    firing = [a for a in data if a.get("status", {}).get("state") == "active"]
    if not firing:
        return "Активных алертов нет."
    return f"<b>Активные алерты: {len(firing)}</b>\n\n" + "\n\n".join(_fmt_firing(a) for a in firing)


def _fmt_watchdog_down(error: str) -> str:
    return ("<b>Мониторинг недоступен</b>\nAlertmanager не отвечает, о новых проблемах бот сейчас не узнает.\n"
            f"Последняя ошибка: {html.escape(error)}")


def _fmt_watchdog_up() -> str:
    return "<b>Мониторинг снова доступен</b>"


async def process_alerts(data: List[dict]) -> None:
    """One poll: announce new firing alerts and alerts that have resolved since the last poll."""
    current = {}
    for a in data:
        if a.get("status", {}).get("state") != "active":
            continue
        fp = a.get("fingerprint")
        if not fp:
            continue
        current[fp] = a
        if db.get_alert_status(fp) != "firing":
            await _broadcast(_fmt_firing(a))
            db.upsert_alert(fp, "firing", a.get("labels", {}).get("alertname", "alert"))
    for fp, name in db.list_firing_fingerprints():
        if fp not in current:
            await _broadcast(_fmt_resolved(name))
            db.upsert_alert(fp, "resolved", name)
    db.purge_old_resolved()


class Watchdog:
    """Counts failed polls in a row; reports once when monitoring is lost and once when it is back."""

    def __init__(self, threshold: int):
        self.threshold = threshold
        self.failures = 0
        self.reported = False

    async def failed(self, error: str) -> None:
        self.failures += 1
        if self.failures >= self.threshold and not self.reported:
            self.reported = True
            await _broadcast(_fmt_watchdog_down(error))

    async def ok(self) -> None:
        if self.reported:
            await _broadcast(_fmt_watchdog_up())
        self.failures = 0
        self.reported = False


async def alert_poller():
    log.info("alert poller started (every %ss)", ALERT_POLL_SECONDS)
    watchdog = Watchdog(ALERT_WATCHDOG_FAILURES)
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await process_alerts(await _fetch_alerts(session))
                await watchdog.ok()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.warning("alert poll failed: %s", e)
                await watchdog.failed(str(e) or type(e).__name__)
            await asyncio.sleep(ALERT_POLL_SECONDS)
