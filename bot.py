import asyncio
import logging
import os
import sys

from aiogram.types import BotCommand

from init import bot, dp
from handlers import router, alert_poller

_log_handlers = [logging.StreamHandler(sys.stdout)]
# File log is optional: in Docker set ALERTBOT_LOG_FILE= (empty) and read `docker logs`
if os.environ.get("ALERTBOT_LOG_FILE", "bot.log"):
    _log_handlers.append(logging.FileHandler(os.environ.get("ALERTBOT_LOG_FILE", "bot.log"), encoding="utf-8"))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=_log_handlers,
)
log = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="servers", description="CPU / RAM / диск / аптайм по узлам"),
    BotCommand(command="services", description="что работает и что нет"),
    BotCommand(command="certs", description="дни до истечения TLS"),
    BotCommand(command="alerts", description="активные алерты (on/off — подписка)"),
    BotCommand(command="status", description="что включено"),
    BotCommand(command="help", description="справка"),
]


async def main() -> None:
    log.info("alertbot starting")
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await bot.set_my_commands(COMMANDS)
    except Exception as e:
        log.warning("set_my_commands failed: %s", e)

    poller = asyncio.create_task(alert_poller())
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(),
                               timeout=20, relax=0.1)
    finally:
        poller.cancel()
        await bot.session.close()
        log.info("alertbot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
