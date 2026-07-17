"""Low-level HTTP client for the MAX Bot API (platform-api2.max.ru)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(15.0, connect=8.0)


def max_configured() -> bool:
    return bool(settings.MAX_BOT_TOKEN.strip())


def _headers() -> dict[str, str]:
    return {
        "Authorization": settings.MAX_BOT_TOKEN.strip(),
        "Content-Type": "application/json",
    }


def _base() -> str:
    return settings.MAX_API_BASE.rstrip("/")


async def max_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Perform an authenticated MAX API call. Returns parsed JSON or None on failure."""
    if not max_configured():
        logger.warning("MAX_BOT_TOKEN is not configured; skipping %s %s", method, path)
        return None

    url = f"{_base()}{path}"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.request(
                method,
                url,
                headers=_headers(),
                params=params,
                json=json_body,
            )
            if response.status_code >= 400:
                logger.error(
                    "MAX API %s %s failed: %s %s",
                    method,
                    path,
                    response.status_code,
                    response.text[:500],
                )
                return None
            if not response.content:
                return {}
            return response.json()
    except Exception:  # noqa: BLE001
        logger.exception("MAX API %s %s raised", method, path)
        return None


async def send_max_message(
    *,
    text: str,
    user_id: int | None = None,
    chat_id: int | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> bool:
    """Send a message to a MAX user or chat. Returns True on success."""
    if not user_id and not chat_id:
        logger.warning("send_max_message called without user_id/chat_id")
        return False

    params: dict[str, Any] = {}
    if user_id is not None:
        params["user_id"] = user_id
    if chat_id is not None:
        params["chat_id"] = chat_id

    body: dict[str, Any] = {"text": text}
    if attachments:
        body["attachments"] = attachments

    result = await max_request("POST", "/messages", params=params, json_body=body)
    if result is None:
        return False
    logger.info("MAX message sent to user_id=%s chat_id=%s", user_id, chat_id)
    return True


def confirm_booking_keyboard(appointment_id: str) -> list[dict[str, Any]]:
    """Inline keyboard with a confirm-booking callback button."""
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [
                        {
                            "type": "callback",
                            "text": "✅ Подтвердить запись",
                            "payload": f"confirm:{appointment_id}",
                        }
                    ]
                ]
            },
        }
    ]


def contact_request_keyboard() -> list[dict[str, Any]]:
    """Inline keyboard asking the user to share their phone contact."""
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [
                        {
                            "type": "request_contact",
                            "text": "📱 Мои записи",
                        }
                    ]
                ]
            },
        }
    ]


async def subscribe_webhook(url: str, secret: str) -> bool:
    """Register HTTPS webhook subscription for bot updates."""
    body = {
        "url": url,
        "update_types": [
            "message_created",
            "bot_started",
            "message_callback",
        ],
        "secret": secret,
    }
    result = await max_request("POST", "/subscriptions", json_body=body)
    if result is None:
        return False
    logger.info("MAX webhook subscribed: %s", url)
    return True


async def get_subscriptions() -> list[Any]:
    result = await max_request("GET", "/subscriptions")
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        subs = result.get("subscriptions") or result.get("list") or []
        return subs if isinstance(subs, list) else []
    return []
