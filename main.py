import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from database import init_db
from handlers import admin, user

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # admin-роутер подключаем первым, чтобы /admin и его callback'и обрабатывались
    # только у админов раньше общих хендлеров
    dp.include_router(admin.router)
    dp.include_router(user.router)

    logger.info("Бот-магазин запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
