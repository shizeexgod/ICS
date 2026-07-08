"""Low-level Telegram Bot API helper for outbound notifications."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


async def send_tg_notification(chat_id: str, text: str) -> bool:
    """Send a text message to a Telegram chat via the Bot API."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not configured.")
        return False

    url = TELEGRAM_API_BASE.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
            if not body.get("ok"):
                logger.error("Telegram API returned ok=false: %s", body)
                return False
        logger.info("Telegram notification delivered to chat_id=%s", chat_id)
        return True
    except httpx.HTTPStatusError:
        logger.exception(
            "Telegram HTTP error for chat_id=%s status=%s",
            chat_id,
            getattr(response, "status_code", "?"),
        )
        return False
    except httpx.RequestError:
        logger.exception("Network error sending Telegram notification to chat_id=%s", chat_id)
        return False
