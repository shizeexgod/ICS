"""Notification template catalog, defaults, and formatting."""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Any

from app.core.db import supabase
from app.utils.formatters import format_template

logger = logging.getLogger(__name__)

TEMPLATE_CATALOG: dict[str, dict[str, Any]] = {
    "reminder": {
        "title": "Напоминание о записи",
        "description": "За 2 часа до визита клиенту в WhatsApp/SMS.",
        "channel": "client",
        "placeholders": [
            "client_name",
            "company_name",
            "service_name",
            "appointment_date",
            "appointment_time",
        ],
        "default": (
            "Здравствуйте, {client_name}! Напоминаем: {appointment_date} в {appointment_time} "
            "у вас запись «{service_name}» в «{company_name}». Ждём вас!"
        ),
    },
    "booking_confirmed": {
        "title": "Подтверждение записи",
        "description": "Клиенту после подтверждения записи администратором.",
        "channel": "client",
        "placeholders": [
            "client_name",
            "company_name",
            "service_name",
            "appointment_date",
            "appointment_time",
        ],
        "default": (
            "✅ Ваша запись на «{service_name}» {appointment_date} в {appointment_time} "
            "в «{company_name}» подтверждена!"
        ),
    },
    "booking_cancelled": {
        "title": "Отмена записи",
        "description": "Клиенту при отмене записи в кабинете или Telegram.",
        "channel": "client",
        "placeholders": [
            "client_name",
            "company_name",
            "service_name",
            "appointment_date",
            "appointment_time",
        ],
        "default": (
            "Ваша запись на «{service_name}» {appointment_date} в {appointment_time} "
            "в «{company_name}» отменена. Для новой записи свяжитесь с нами."
        ),
    },
    "new_booking": {
        "title": "Новая запись (Telegram)",
        "description": "Администраторам в Telegram при создании записи.",
        "channel": "telegram",
        "placeholders": [
            "company_name",
            "client_name",
            "client_phone",
            "service_name",
            "appointment_date",
            "appointment_time",
        ],
        "default": (
            "🆕 *Новая запись*\n\n"
            "🏢 *Компания:* {company_name}\n"
            "👤 *Клиент:* {client_name}\n"
            "📞 *Телефон:* {client_phone}\n"
            "💈 *Услуга:* {service_name}\n"
            "📅 *Дата:* {appointment_date}\n"
            "🕒 *Время:* {appointment_time}"
        ),
    },
}


def _format_date(value: dt.date | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d.%m.%Y")


def _format_time(value: dt.time | None) -> str:
    if value is None:
        return ""
    return value.strftime("%H:%M")


def build_appointment_context(
    *,
    client_name: str = "",
    client_phone: str = "",
    company_name: str = "",
    service_name: str = "",
    appointment_date: dt.date | None = None,
    appointment_time: dt.time | None = None,
) -> dict[str, str]:
    return {
        "client_name": client_name,
        "client_phone": client_phone,
        "company_name": company_name,
        "service_name": service_name,
        "appointment_date": _format_date(appointment_date),
        "appointment_time": _format_time(appointment_time),
    }


async def seed_default_templates(company_id: uuid.UUID) -> None:
    """Insert default templates for a new company (idempotent)."""
    rows = [
        {
            "company_id": str(company_id),
            "event_type": event_type,
            "tg_template": meta["default"],
            "is_enabled": True,
        }
        for event_type, meta in TEMPLATE_CATALOG.items()
    ]
    try:
        await (
            supabase.table("notification_templates")
            .upsert(rows, on_conflict="company_id,event_type")
            .execute_async()
        )
    except Exception:
        logger.exception("Failed to seed default templates for company_id=%s", company_id)


async def list_company_templates(company_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return all catalog templates merged with company overrides."""
    stored: dict[str, dict[str, Any]] = {}
    try:
        result = await (
            supabase.table("notification_templates")
            .select("event_type", "tg_template", "is_enabled")
            .eq("company_id", str(company_id))
            .execute_async()
        )
        for row in result.data or []:
            stored[row["event_type"]] = row
    except Exception:
        logger.exception("Failed to load templates for company_id=%s", company_id)

    items: list[dict[str, Any]] = []
    for event_type, meta in TEMPLATE_CATALOG.items():
        row = stored.get(event_type, {})
        items.append(
            {
                "event_type": event_type,
                "title": meta["title"],
                "description": meta["description"],
                "channel": meta["channel"],
                "placeholders": meta["placeholders"],
                "tg_template": row.get("tg_template") or meta["default"],
                "is_enabled": bool(row.get("is_enabled", True)),
                "is_customized": event_type in stored,
            }
        )
    return items


async def get_template_text(
    company_id: uuid.UUID,
    event_type: str,
    *,
    context: dict[str, str] | None = None,
) -> tuple[str | None, bool]:
    """Return formatted message text and whether the template is enabled."""
    if event_type not in TEMPLATE_CATALOG:
        return None, False

    meta = TEMPLATE_CATALOG[event_type]
    template_text = meta["default"]
    is_enabled = True

    try:
        result = await (
            supabase.table("notification_templates")
            .select("tg_template", "is_enabled")
            .eq("company_id", str(company_id))
            .eq("event_type", event_type)
            .execute_async()
        )
        rows = result.data or []
        if rows:
            template_text = rows[0].get("tg_template") or template_text
            is_enabled = bool(rows[0].get("is_enabled", True))
    except Exception:
        logger.exception(
            "Failed to fetch template company_id=%s event_type=%s", company_id, event_type
        )

    if not is_enabled:
        return None, False

    if context:
        return format_template(template_text, context), True
    return template_text, True
