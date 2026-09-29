# AlertBot

Telegram-бот для мониторинга парка серверов поверх Prometheus + Alertmanager. Работает как
push-уведомитель («что-то сломалось / починилось») и как справочная панель по команде
(`/servers`, `/services`, `/certs`).

## Возможности

- **Алерты в реальном времени** — фоновая задача раз в N секунд опрашивает Alertmanager,
  дедуплицирует по fingerprint и сразу шлёт «Проблема · …» / «В норме · …» подписанным
  пользователям. Никаких собственных правил — подхватывает всё, что уже настроено в
  Alertmanager, по лейблам, а не по именам целей.
- **`/servers`** — CPU, RAM, диск, swap, load, аптайм и (если есть hwmon-датчики)
  температура по каждому узлу, с ⚠ при превышении порогов.
- **`/services`** — какие цели Prometheus сейчас `up`, какие нет.
- **`/certs`** — сколько дней осталось у каждого TLS-сертификата, с предупреждением при <14 дней.
- **`/alerts`** — список активных алертов сейчас; `/alerts on|off` — подписка/отписка.
- Доступ — по вайтлисту Telegram user id, все остальные тихо игнорируются.

## Требования

- Python 3.10+
- Свой Prometheus + Alertmanager с уже настроенными правилами алертов.
- Alertmanager и Prometheus должны быть доступны боту по HTTP — либо напрямую (если бот
  крутится на той же машине), либо через reverse-proxy с токен-параметром в URL (так это
  сделано в этом проекте — см. `AM_ALERTS_URL`/`PROM_QUERY_URL`/`AM_TOKEN`/`PROM_TOKEN`
  в `.env.example`), чтобы не открывать сами Prometheus/Alertmanager в интернет без авторизации.

## Установка

```bash
pip install -r requirements.txt
cp .env.example .env
# заполнить .env своими значениями
python bot.py
```

## Переменные окружения

Все — в `.env.example`:

- `BOT_TOKEN` — токен бота от @BotFather.
- `ALLOWED_IDS` — Telegram user id через запятую, кому разрешено пользоваться ботом.
- `AM_ALERTS_URL` / `PROM_QUERY_URL` / `AM_TOKEN` / `PROM_TOKEN` — адреса и токены до
  Alertmanager API (`/api/v2/alerts`) и Prometheus API (`/api/v1/query`).
- `SERVERS_ORDER` — имена узлов через запятую, ровно как они указаны в лейбле `server`
  у твоих метрик (`node_exporter` и т.п.) — определяет порядок и состав вывода `/servers`.
- `ALERT_POLL_SECONDS` / `ALERT_HTTP_TIMEOUT` — период опроса и таймаут запросов.

## Структура

```
init.py       # конфиг из переменных окружения, инициализация Bot/Dispatcher
sql.py        # SQLite: подписчики на алерты, дедуп по fingerprint
handlers.py   # команды бота + фоновый опрос Alertmanager
bot.py        # точка входа
```

Хранилище — один файл SQLite (`notifications.db`, путь по умолчанию задаётся при
инициализации `DatabaseManager`), без внешних зависимостей вроде Redis/Postgres.

## Продакшен

Юнит `systemd` — самый простой способ держать бота в фоне постоянно:

```ini
[Unit]
Description=AlertBot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/alertbot
ExecStart=/opt/alertbot/venv/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Лицензия

MIT
