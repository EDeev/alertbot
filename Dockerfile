FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    ALERTBOT_LOG_FILE= \
    PYTHONUNBUFFERED=1 \
    ALERTBOT_DB=/data/notifications.db

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
RUN useradd --create-home --uid 1000 app && mkdir -p /data && chown -R app:app /app /data
USER app
VOLUME ["/data"]

CMD ["python", "bot.py"]
