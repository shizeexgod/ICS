"""MAX fan-out helpers for multi-tenant booking notifications (staff)."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.max_api import confirm_booking_keyboard, max_configured, send_max_message
from app.services.staff_service import get_notification_max_user_ids
from app.services.template_service import build_appointment_context, get_template_text

logger = logging.getLogger(__name__)


def _strip_telegram_markdown(text: str) -> str:
    """MAX messages are plain text; drop common Telegram Markdown markers."""
    return (
        text.replace("*", "")
        .replace("_", "")
        .replace("`", "")
    )


async def notify_company_managers_of_new_booking_max(
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
    """Send a new-booking card to every MAX-bound staff member of the company."""
    if not max_configured():
        return

    user_ids = await get_notification_max_user_ids(session, company_id)
    if not user_ids:
        logger.info(
            "No MAX managers for company_id=%s (%s); skipping MAX staff notification.",
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
            "new_booking template disabled for company_id=%s; skipping MAX notification.",
            company_id,
        )
        return

    plain = _strip_telegram_markdown(message_text)
    attachments = confirm_booking_keyboard(str(appointment_id))

    try:
        results = await asyncio.gather(
            *(
                send_max_message(
                    text=plain,
                    user_id=user_id,
                    attachments=attachments,
                )
                for user_id in user_ids
            ),
            return_exceptions=True,
        )
        for user_id, result in zip(user_ids, results):
            if isinstance(result, Exception):
                logger.exception(
                    "Failed to send MAX notification to user_id=%s",
                    user_id,
                    exc_info=result,
                )
            elif result is False:
                logger.error("MAX notification rejected for user_id=%s", user_id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "Booking saved but MAX staff notification failed for company_id=%s", company_id
        )
