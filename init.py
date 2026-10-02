import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import DefaultBotProperties

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]

# Only these Telegram user ids may use the bot. Add friends' ids here if needed.
ALLOWED_IDS = {int(x) for x in os.environ.get("ALLOWED_IDS", "").split(",") if x.strip()}

# --- Monitoring APIs (pull via token-auth reverse-proxy paths, no basic-auth) ---
AM_ALERTS_URL = os.environ["AM_ALERTS_URL"]
PROM_QUERY_URL = os.environ["PROM_QUERY_URL"]
AM_TOKEN = os.environ["AM_TOKEN"]
PROM_TOKEN = os.environ["PROM_TOKEN"]
ALERT_POLL_SECONDS = int(os.environ.get("ALERT_POLL_SECONDS", "45"))
ALERT_HTTP_TIMEOUT = int(os.environ.get("ALERT_HTTP_TIMEOUT", "15"))
# After this many failed polls in a row the bot reports that monitoring itself is unreachable
ALERT_WATCHDOG_FAILURES = int(os.environ.get("ALERT_WATCHDOG_FAILURES", "4"))
DB_PATH = os.environ.get("ALERTBOT_DB", "notifications.db")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
