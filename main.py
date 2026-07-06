import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from database import init_db
from handlers import admin, user
from services.payment_watcher import poll_payments

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(admin.router)
    dp.include_router(user.router)

    poller_task = asyncio.create_task(poll_payments(bot))

    logger.info("Бот-магазин запущен")
    try:
        await dp.start_polling(bot)
    finally:
        poller_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
