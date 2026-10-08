"""Entry point for the AI swimming coach Telegram bot."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from app.handlers import start_router, survey_router, workout_router


def setup_logging(log_level: str) -> None:
    """Configure global application logging."""

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    """Initialize the bot and start long polling."""

    settings = get_settings()
    setup_logging(settings.log_level)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(survey_router)
    dp.include_router(workout_router)

    logging.getLogger(__name__).info("Bot started.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logging.getLogger(__name__).info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())

