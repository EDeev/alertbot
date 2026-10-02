import asyncio

import handlers
from tests.conftest import vec


def run(coro):
    return asyncio.run(coro)


def test_uptime_format():
    assert handlers.fmt_uptime(3 * 86400 + 5 * 3600) == "3д 5ч"
    assert handlers.fmt_uptime(7200) == "2ч"
    assert handlers.fmt_uptime(-5) == "0ч"


def test_servers_report_marks_problems(prom):
    import time

    now = time.time()
    prom.update({
        "up{": vec(spb=1, ams=0),
        "node_cpu_seconds_total": vec(spb=12, ams=3),
        "MemAvailable": vec(spb=95, ams=40),
        "node_filesystem_avail_bytes": vec(spb=50, ams=91),
        "node_load1": vec(spb=0.5, ams=0.1),
        "node_boot_time_seconds": vec(spb=now - 2 * 86400, ams=now - 3600),
        "SwapTotal": vec(spb=0, ams=0),
        "hwmon": vec(spb=40),
    })
    text = run(handlers.render_servers())
    assert "<b>SPB</b> · ⚠ память" in text
    assert "<b>AMS</b> · НЕ ОТВЕЧАЕТ" in text
    assert "<b>DORM</b> — нет данных" in text
    assert "аптайм 2д 0ч" in text


def test_services_report(prom):
    prom["up"] = [
        {"metric": {"job": "node_spb", "instance": "spb:9100"}, "value": [0, "1"]},
        {"metric": {"job": "blackbox_http", "instance": "https://<bad>.example"}, "value": [0, "0"]},
    ]
    text = run(handlers.render_services())
    assert "1/2 в норме" in text
    assert "&lt;bad&gt;" in text


def test_services_all_ok(prom):
    prom["up"] = [{"metric": {"job": "node_spb"}, "value": [0, "1"]}]
    assert "Все 1 в норме" in run(handlers.render_services())


def test_certs_report_sorted_with_warning(prom):
    prom["probe_ssl_earliest_cert_expiry"] = [
        {"metric": {"instance": "https://deev.space/"}, "value": [0, "60.2"]},
        {"metric": {"instance": "https://tablo.deev.su"}, "value": [0, "5.1"]},
    ]
    text = run(handlers.render_certs())
    assert "скоро истекают: tablo.deev.su — 5 дн" in text
    rows = text.split("<pre>")[1].split("</pre>")[0].splitlines()
    assert rows[0].endswith("tablo.deev.su") and rows[1].endswith("deev.space")


def test_prometheus_error_is_reported(monkeypatch):
    async def boom(session, query):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(handlers, "_promq", boom)
    assert "Не удалось получить метрики" in run(handlers.render_servers())
