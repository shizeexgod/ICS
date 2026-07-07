"""Aiogram v3 Bot/Dispatcher setup and lifecycle helpers (long-polling mode)."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import router
from app.core.config import settings

logger = logging.getLogger(__name__)

bot: Bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dispatcher: Dispatcher = Dispatcher()
dispatcher.include_router(router)

_polling_task: asyncio.Task[None] | None = None


async def start_bot_polling() -> None:
    """Start long-polling in the background. Intended to be called from FastAPI's lifespan."""
    global _polling_task

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting Telegram bot polling.")
    _polling_task = asyncio.create_task(
        dispatcher.start_polling(bot, handle_signals=False),
        name="telegram-bot-polling",
    )


async def stop_bot_polling() -> None:
    """Gracefully stop polling and close the bot session."""
    global _polling_task

    logger.info("Stopping Telegram bot polling.")
    await dispatcher.stop_polling()

    if _polling_task is not None:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
        _polling_task = None

    await bot.session.close()
