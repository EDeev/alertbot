# AlertBot

[Русский](README.md) · **English**

[![CI](https://github.com/EDeev/alertbot/actions/workflows/ci.yml/badge.svg)](https://github.com/EDeev/alertbot/actions/workflows/ci.yml)
[![Docker](https://github.com/EDeev/alertbot/actions/workflows/docker.yml/badge.svg)](https://github.com/EDeev/alertbot/actions/workflows/docker.yml)
[![Release](https://img.shields.io/github/v/release/EDeev/alertbot)](https://github.com/EDeev/alertbot/releases)
[![License](https://img.shields.io/github/license/EDeev/alertbot)](LICENSE)

A Telegram bot for monitoring a small server fleet on top of Prometheus and Alertmanager: it sends
"problem / resolved" alerts and, on command, shows the state of servers, services and TLS certificates.

**Status:** personal project, in production · watches the author's five servers

```text
Серверы

SPB
CPU 7% · RAM 41% · диск 38% · swap 0%
load 0.21 · аптайм 12д 4ч

DORM · ⚠ диск
CPU 18% · RAM 63% · диск 87% · swap 2% · temp 52°C
load 1.40 · аптайм 3д 9ч
```

<sub>Sample <code>/servers</code> reply (illustrative values; the bot speaks Russian).</sub>

**Stack:** Python 3.10+ · aiogram 3 · aiohttp · SQLite · Prometheus HTTP API · Alertmanager API v2 · Docker

## Features

- **Alerts:** polls Alertmanager every N seconds, deduplicates by fingerprint and immediately notifies
  subscribers about new and resolved alerts. No rules of its own — whatever Alertmanager has
- **Watchdog:** if Alertmanager itself stops responding, the bot reports it once and again when
  monitoring is back
- **`/servers`** — CPU, RAM, disk, swap, load, uptime and temperature per node, ⚠ above thresholds
- **`/services`** — which Prometheus targets are down
- **`/certs`** — days until TLS certificates expire, warning under 14 days
- **`/alerts`** — active alerts; `/alerts on|off` — subscription
- Access is limited to a list of Telegram IDs; everyone else is silently ignored

## Quick start

```bash
git clone https://github.com/EDeev/alertbot.git && cd alertbot
cp .env.example .env      # bot token, IDs, Prometheus/Alertmanager URLs and tokens
docker compose up -d
```

Prebuilt image: `docker pull ghcr.io/edeev/alertbot` or `docker pull git.deev.su/edeev/alertbot`.

## Installing without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## Configuration

| Variable | Purpose |
|---|---|
| `BOT_TOKEN` | bot token from @BotFather |
| `ALLOWED_IDS` | comma-separated Telegram IDs allowed to use the bot |
| `AM_ALERTS_URL`, `PROM_QUERY_URL` | Alertmanager `/api/v2/alerts` and Prometheus `/api/v1/query` |
| `AM_TOKEN`, `PROM_TOKEN` | tokens sent in the `Authorization: Bearer` header |
| `SERVERS_ORDER` | comma-separated node names as in the metrics' `server` label |
| `ALERT_POLL_SECONDS`, `ALERT_HTTP_TIMEOUT` | poll interval and request timeout |
| `ALERT_WATCHDOG_FAILURES` | failed polls in a row before reporting monitoring as unreachable (default 4) |
| `ALERTBOT_DB`, `ALERTBOT_LOG_FILE` | SQLite file and log file (empty means stdout only) |

> [!IMPORTANT]
> Do not expose Prometheus and Alertmanager to the internet without authentication. The bot expects a
> reverse proxy that checks the `Authorization: Bearer …` token; see the nginx example in
> [docs/deploy.md](docs/deploy.md) (in Russian).

## Deployment

The bot runs on a separate VPS as a systemd unit. Prometheus and Alertmanager live on another server
behind nginx, which lets the bot in only with a token. GitHub Actions builds the Docker image on every
`v*` tag and publishes it to GitHub Packages and to `git.deev.su`.

## Development

```bash
pip install -r requirements-dev.txt
ruff check . && pytest
```

The tests need no network: Telegram and Prometheus are faked. They cover alert deduplication,
resolved notifications, the watchdog and report texts.

## License

MIT — see [LICENSE](LICENSE).

## Author

**Egor Deev** — [GitHub](https://github.com/EDeev) · [Telegram](https://t.me/DeevEgor) · [egor@deev.space](mailto:egor@deev.space)

---

<div align="center">
  <sub>⭐ If you find this project useful, give it a star on GitHub!</sub>
  <p><sub>Made with ❤️ — <a href="https://deev.space">deev.space</a></sub></p>
</div>
