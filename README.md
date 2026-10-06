# AlertBot

**Русский** · [English](README.en.md)

[![CI](https://github.com/EDeev/alertbot/actions/workflows/ci.yml/badge.svg)](https://github.com/EDeev/alertbot/actions/workflows/ci.yml)
[![Docker](https://github.com/EDeev/alertbot/actions/workflows/docker.yml/badge.svg)](https://github.com/EDeev/alertbot/actions/workflows/docker.yml)
[![Release](https://img.shields.io/github/v/release/EDeev/alertbot)](https://github.com/EDeev/alertbot/releases)
[![License](https://img.shields.io/github/license/EDeev/alertbot)](LICENSE)

Telegram-бот для мониторинга парка серверов поверх Prometheus и Alertmanager: присылает алерты
«проблема / в норме» и по команде показывает состояние серверов, сервисов и TLS-сертификатов.

**Статус:** личный проект, работает · следит за пятью серверами автора

```text
Серверы

SPB
CPU 7% · RAM 41% · диск 38% · swap 0%
load 0.21 · аптайм 12д 4ч

DORM · ⚠ диск
CPU 18% · RAM 63% · диск 87% · swap 2% · temp 52°C
load 1.40 · аптайм 3д 9ч
```

<sub>Пример ответа на <code>/servers</code> (значения условные).</sub>

**Стек:** Python 3.10+ · aiogram 3 · aiohttp · SQLite · Prometheus HTTP API · Alertmanager API v2 · Docker

## Возможности

- **Алерты:** раз в N секунд опрашивает Alertmanager, дедуплицирует по fingerprint и сразу пишет
  «Проблема · …» и «В норме · …» подписчикам. Своих правил нет — всё, что настроено в Alertmanager
- **Сторож:** если сам Alertmanager перестал отвечать, бот один раз сообщает об этом и ещё раз —
  когда мониторинг вернулся
- **`/servers`** — CPU, RAM, диск, swap, load, аптайм и температура по узлам, ⚠ при превышении порогов
- **`/services`** — какие цели Prometheus не отвечают
- **`/certs`** — дни до истечения TLS-сертификатов, предупреждение меньше чем за 14 дней
- **`/alerts`** — активные алерты; `/alerts on|off` — подписка
- Доступ — только для Telegram ID из списка, остальные молча игнорируются

## Быстрый старт

```bash
git clone https://github.com/EDeev/alertbot.git && cd alertbot
cp .env.example .env      # токен бота, ID, адреса и токены Prometheus/Alertmanager
docker compose up -d
```

Готовый образ: `docker pull ghcr.io/edeev/alertbot` или `docker pull git.deev.su/edeev/alertbot`.

## Установка без Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## Конфигурация

| Переменная | Назначение |
|---|---|
| `BOT_TOKEN` | токен бота от @BotFather |
| `ALLOWED_IDS` | Telegram ID через запятую, кому можно пользоваться ботом |
| `AM_ALERTS_URL`, `PROM_QUERY_URL` | Alertmanager `/api/v2/alerts` и Prometheus `/api/v1/query` |
| `AM_TOKEN`, `PROM_TOKEN` | токены, бот передаёт их в заголовке `Authorization: Bearer` |
| `SERVERS_ORDER` | имена узлов через запятую, как в лейбле `server` метрик |
| `ALERT_POLL_SECONDS`, `ALERT_HTTP_TIMEOUT` | период опроса и таймаут запросов |
| `ALERT_WATCHDOG_FAILURES` | после скольких неудачных опросов подряд сообщать о недоступности (по умолчанию 4) |
| `ALERTBOT_DB`, `ALERTBOT_LOG_FILE` | файл SQLite и файл лога (пусто — только stdout) |

> [!IMPORTANT]
> Не открывайте Prometheus и Alertmanager в интернет без авторизации. Бот рассчитан на обратный прокси,
> который проверяет токен из заголовка `Authorization: Bearer …`, — пример для nginx в
> [docs/deploy.md](docs/deploy.md).

## Развёртывание

Бот работает на отдельном VPS как systemd-юнит. Prometheus и Alertmanager стоят на другом сервере
за nginx, который пускает бота только с токеном. Docker-образ собирает GitHub Actions на каждый тег
`v*` и публикует в GitHub Packages и в реестр `git.deev.su`.

## Разработка

```bash
pip install -r requirements-dev.txt
ruff check . && pytest
```

Тесты работают без сети: Telegram и Prometheus подменяются. Проверяются дедупликация алертов,
сообщения о возврате в норму, сторож и тексты сводок.

## Лицензия

MIT — см. [LICENSE](LICENSE).

## Автор

**Деев Егор Викторович** — [GitHub](https://github.com/EDeev) · [Telegram](https://t.me/DeevEgor) · [egor@deev.space](mailto:egor@deev.space)

---

<div align="center">
  <sub>⭐ Если проект оказался полезным, поставьте звёздочку на GitHub!</sub>
  <p><sub>Сделано с ❤️ — <a href="https://deev.space">deev.space</a></sub></p>
</div>
