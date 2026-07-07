"""Client-facing notification channels: WhatsApp (Green-API) and SMS (SMS.ru).

Both senders are best-effort: they log failures and return `False` instead of
raising, so a broken/misconfigured channel never crashes the caller (a webhook
request, a scheduled reminder job, or a Telegram callback handler).
"""

from __future__ import annotations

import asyncio
import logging
import re

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def clean_phone_number(phone: str) -> str:
    """Keep digits only and normalize Russian numbers to ``7XXXXXXXXXX``.

    Examples:
        ``+7 (999) 111-22-33`` -> ``79991112233``
        ``89991112233``        -> ``79991112233``
    """
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("8"):
        return "7" + digits[1:]
    return digits


async def send_whatsapp(phone: str, message: str) -> bool:
    """Send a WhatsApp message via Green-API."""
    return await send_client_whatsapp(phone, message)


async def send_sms(phone: str, message: str) -> bool:
    """Send an SMS via SMS.ru."""
    return await send_client_sms(phone, message)


async def send_client_whatsapp(phone: str, message: str) -> bool:
    """Send a WhatsApp message to `phone` via Green-API.

    If Green-API credentials are missing, logs a dry-run imitation instead of
    calling the API. Returns True on a confirmed send (or dry-run), False on error.
    """
    if not settings.GREEN_API_INSTANCE or not settings.GREEN_API_TOKEN:
        clean_phone = clean_phone_number(phone)
        logger.info(
            "[DRY-RUN WhatsApp] to=%s message=%r (GREEN_API_INSTANCE/GREEN_API_TOKEN not set)",
            clean_phone or phone,
            message,
        )
        return True

    return await _send_whatsapp_via_green_api(phone, message)


async def send_client_sms(phone: str, message: str) -> bool:
    """Send an SMS to `phone` via SMS.ru.

    If SMS.ru credentials are missing, logs a dry-run imitation instead of
    calling the API. Returns True on a confirmed send (or dry-run), False on error.
    """
    if not settings.SMS_RU_API_KEY:
        clean_phone = clean_phone_number(phone)
        logger.info(
            "[DRY-RUN SMS] to=%s message=%r (SMS_RU_API_KEY not set)",
            clean_phone or phone,
            message,
        )
        return True

    return await _send_sms_via_sms_ru(phone, message)


async def send_whatsapp_message(phone: str, text: str) -> bool:
    """Backward-compatible alias for :func:`send_client_whatsapp`."""
    return await send_client_whatsapp(phone, text)


async def send_sms_message(phone: str, text: str) -> bool:
    """Backward-compatible alias for :func:`send_client_sms`."""
    return await send_client_sms(phone, text)


async def _send_whatsapp_via_green_api(phone: str, text: str) -> bool:
    """Low-level Green-API sender (requires credentials in `.env`)."""
    clean_phone = clean_phone_number(phone)
    if not clean_phone:
        logger.warning("Cannot send WhatsApp message: empty/invalid phone number %r.", phone)
        return False

    url = (
        f"https://api.green-api.com/waInstance{settings.GREEN_API_INSTANCE}"
        f"/sendMessage/{settings.GREEN_API_TOKEN}"
    )
    payload = {"chatId": f"{clean_phone}@c.us", "message": text}

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        logger.info("WhatsApp message sent to %s via Green-API.", clean_phone)
        return True
    except Exception:  # noqa: BLE001 - notification failures must never propagate
        logger.exception("Failed to send WhatsApp message to %s via Green-API.", clean_phone)
        return False


async def _send_sms_via_sms_ru(phone: str, text: str) -> bool:
    """Low-level SMS.ru sender (requires credentials in `.env`)."""
    clean_phone = clean_phone_number(phone)
    if not clean_phone:
        logger.warning("Cannot send SMS: empty/invalid phone number %r.", phone)
        return False

    url = "https://sms.ru/sms/send"
    params = {
        "api_id": settings.SMS_RU_API_KEY,
        "to": clean_phone,
        "msg": text,
        "json": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception:  # noqa: BLE001 - notification failures must never propagate
        logger.exception("Failed to send SMS to %s via SMS.ru.", clean_phone)
        return False

    if data.get("status") != "OK":
        logger.error("SMS.ru rejected the message to %s: %s", clean_phone, data)
        return False

    logger.info("SMS sent to %s via SMS.ru.", clean_phone)
    return True


async def notify_client(phone: str, text: str) -> None:
    """Best-effort fan-out of a client-facing text to both WhatsApp and SMS.

    Both channels are attempted in parallel; a failure on one channel does not
    prevent the other from being tried, and neither failure raises.
    """
    await asyncio.gather(
        send_client_whatsapp(phone, text),
        send_client_sms(phone, text),
        return_exceptions=True,
    )
