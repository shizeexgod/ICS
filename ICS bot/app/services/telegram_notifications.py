"""Telegram fan-out helpers for multi-tenant booking notifications."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import uuid

from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import ConfirmBookingCallback
from app.bot.main import bot
from app.models.company_manager import CompanyManager
from app.services.template_service import build_appointment_context, get_template_text

logger = logging.getLogger(__name__)


async def get_manager_chat_ids(session: AsyncSession, company_id: uuid.UUID) -> list[int]:
    """Return all Telegram chat ids subscribed to a company's booking notifications."""
    result = await session.execute(
        select(CompanyManager.tg_chat_id).where(CompanyManager.company_id == company_id)
    )
    return list(result.scalars().all())


async def notify_company_managers_of_new_booking(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    appointment_id: uuid.UUID,
    company_name: str,
    client_name: str,
    client_phone: str,
    service_name: str,
    appointment_date: dt.date,
    appointment_time: dt.time,
) -> None:
    """Format and fan out a booking card to every manager of the given company.

    Failures on individual chat ids are logged and swallowed so a broken
    notification never breaks the HTTP response.
    """
    chat_ids = await get_manager_chat_ids(session, company_id)
    if not chat_ids:
        logger.warning(
            "No managers registered for company_id=%s (%s); skipping Telegram notification.",
            company_id,
            company_name,
        )
        return

    context = build_appointment_context(
        client_name=client_name,
        client_phone=client_phone,
        company_name=company_name,
        service_name=service_name,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
    )
    message_text, enabled = await get_template_text(
        company_id, "new_booking", context=context
    )
    if not enabled or not message_text:
        logger.info(
            "new_booking template disabled for company_id=%s; skipping Telegram notification.",
            company_id,
        )
        return

    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.button(
        text="✅ Подтвердить запись",
        callback_data=ConfirmBookingCallback(appointment_id=appointment_id),
    )
    reply_markup = keyboard_builder.as_markup()

    try:
        results = await asyncio.gather(
            *(
                bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup,
                )
                for chat_id in chat_ids
            ),
            return_exceptions=True,
        )
        for chat_id, result in zip(chat_ids, results):
            if isinstance(result, Exception):
                logger.exception(
                    "Failed to send Telegram notification to chat_id=%s",
                    chat_id,
                    exc_info=result,
                )
    except Exception:  # noqa: BLE001 - a failed notification must not fail the booking
        logger.exception(
            "Booking saved but Telegram notification failed for company_id=%s", company_id
        )
