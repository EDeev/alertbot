# Развёртывание

## Docker

```bash
cp .env.example .env
docker compose up -d
docker compose logs -f bot
```

Подписки и состояние алертов хранятся в томе `data` (`/data/notifications.db`).

## systemd

```ini
[Unit]
Description=AlertBot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/alertbot
ExecStart=/opt/alertbot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Обратный прокси перед Prometheus и Alertmanager (nginx)

Бот отправляет токен в заголовке `Authorization: Bearer <токен>`. Пример проверки:

```nginx
# в контексте http (например, /etc/nginx/conf.d/alertbot-auth.conf)
map $http_authorization $alertbot_auth_ok {
    default 0;
    "Bearer ВАШ_ТОКЕН" 1;
}

# в server { ... }
location /prombot/ {
    if ($alertbot_auth_ok = 0) { return 403; }
    proxy_pass http://127.0.0.1:9090/;
}
location /ambot/ {
    if ($alertbot_auth_ok = 0) { return 403; }
    proxy_pass http://127.0.0.1:9093/;
}
```

## Что ожидается от Prometheus

- у метрик node_exporter есть лейбл `server` с короткими именами узлов (как в `SERVERS_ORDER`);
- джобы node_exporter называются `node_*`;
- для `/certs` — blackbox exporter с метрикой `probe_ssl_earliest_cert_expiry`;
- температура берётся из `node_hwmon_temp_celsius` с `chip=~"pci.*"` (настоящие датчики).
