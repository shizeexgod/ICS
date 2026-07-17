"""MAX bot webhook: staff binding, client contact linking, booking confirm callbacks."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.models.company import Company
from app.models.company_staff import CompanyStaff
from app.services.max_api import contact_request_keyboard, send_max_message
from app.services.notifications import notify_client
from app.services.staff_service import (
    bind_staff_max,
    is_staff_max_user,
    normalize_phone,
    normalize_username,
)
from app.services.template_service import build_appointment_context, get_template_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhooks"])

_DIGITS_ONLY_RE = re.compile(r"\D")
_INACTIVE_STATUSES = (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED)


def _clean_phone(phone: str) -> str:
    return _DIGITS_ONLY_RE.sub("", phone or "")


def _extract_user(update: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("user", "from_user", "sender"):
        value = update.get(key)
        if isinstance(value, dict):
            return value
    message = update.get("message")
    if isinstance(message, dict):
        sender = message.get("sender") or message.get("from") or message.get("user")
        if isinstance(sender, dict):
            return sender
    callback = update.get("callback")
    if isinstance(callback, dict):
        user = callback.get("user") or callback.get("from_user")
        if isinstance(user, dict):
            return user
    return None


def _extract_user_id(update: dict[str, Any]) -> int | None:
    user = _extract_user(update)
    if user:
        raw = user.get("user_id") or user.get("id")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None
    message = update.get("message")
    if isinstance(message, dict):
        recipient = message.get("recipient")
        if isinstance(recipient, dict):
            raw = recipient.get("user_id") or recipient.get("chat_id")
            if raw is not None:
                try:
                    return int(raw)
                except (TypeError, ValueError):
                    pass
    return None


def _extract_username(update: dict[str, Any]) -> str | None:
    user = _extract_user(update)
    if not user:
        return None
    return normalize_username(user.get("username") or user.get("login"))


def _extract_text(update: dict[str, Any]) -> str:
    message = update.get("message")
    if isinstance(message, dict):
        body = message.get("body")
        if isinstance(body, dict) and isinstance(body.get("text"), str):
            return body["text"].strip()
        if isinstance(message.get("text"), str):
            return message["text"].strip()
    if isinstance(update.get("text"), str):
        return update["text"].strip()
    return ""


def _phone_from_vcf(vcf: str) -> str | None:
    """Extract the first TEL value from a vCard string."""
    for line in (vcf or "").splitlines():
        raw = line.strip()
        upper = raw.upper()
        if not upper.startswith("TEL"):
            continue
        if ":" not in raw:
            continue
        phone = raw.split(":", 1)[1].strip()
        if phone:
            return phone
    return None


def _extract_contact_phone(update: dict[str, Any]) -> str | None:
    """Pull phone number from a request_contact / contact attachment payload."""
    message = update.get("message")
    if not isinstance(message, dict):
        return None

    body = message.get("body") if isinstance(message.get("body"), dict) else {}
    attachments = message.get("attachments") or body.get("attachments") or []
    if not isinstance(attachments, list):
        return None

    for item in attachments:
        if not isinstance(item, dict):
            continue
        # Some payloads put phone on the attachment itself
        for key in ("phone", "phone_number", "vcf_phone"):
            if item.get(key):
                return str(item[key])

        payload = item.get("payload") or {}
        if isinstance(payload, str):
            phone = _phone_from_vcf(payload)
            if phone:
                return phone
            continue
        if not isinstance(payload, dict):
            continue

        max_info = payload.get("max_info") or {}
        if isinstance(max_info, dict):
            phone = max_info.get("phone") or max_info.get("phone_number")
            if phone:
                return str(phone)

        vcf_info = payload.get("vcf_info")
        if isinstance(vcf_info, str):
            phone = _phone_from_vcf(vcf_info)
            if phone:
                return phone
        elif isinstance(vcf_info, dict):
            phone = vcf_info.get("phone") or vcf_info.get("phone_number")
            if phone:
                return str(phone)

        contact = payload.get("contact")
        if isinstance(contact, dict):
            phone = contact.get("phone") or contact.get("phone_number")
            if phone:
                return str(phone)

        phone = payload.get("phone") or payload.get("phone_number") or payload.get("vcf_phone")
        if phone:
            return str(phone)
    return None


def _extract_callback_payload(update: dict[str, Any]) -> str | None:
    callback = update.get("callback")
    if isinstance(callback, dict):
        payload = callback.get("payload")
        if isinstance(payload, str):
            return payload
    return None


async def _bind_staff_by_api_key(
    *,
    api_key: str,
    max_user_id: int,
    max_username: str | None,
) -> tuple[Company | None, str | None]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Company).where(Company.api_key == api_key))
        company = result.scalars().first()
        if company is None:
            return None, None

        staff, error = await bind_staff_max(
            session,
            company=company,
            max_user_id=max_user_id,
            max_username=max_username,
        )
        if error:
            return None, error

        logger.info(
            "Bound MAX user_id=%s as staff of company_id=%s (%s), staff_id=%s",
            max_user_id,
            company.id,
            company.name,
            staff.id if staff else None,
        )
        return company, None


async def _send_client_greeting(user_id: int, full_name: str | None = None) -> None:
    name = full_name or "друг"
    await send_max_message(
        user_id=user_id,
        text=(
            f"Привет, {name}! 👋\n"
            "Я бот сервиса онлайн-записи ICS.\n\n"
            "Нажмите «Мои записи», чтобы поделиться номером телефона — "
            "я покажу ваши актуальные записи и смогу присылать напоминания в MAX."
        ),
        attachments=contact_request_keyboard(),
    )


async def _handle_staff_or_client_text(
    *,
    max_user_id: int,
    text: str,
    max_username: str | None,
    full_name: str | None,
) -> None:
    maybe_key = text.strip()
    if maybe_key.startswith("/"):
        maybe_key = maybe_key.split(maxsplit=1)[-1].strip() if " " in maybe_key else ""

    if maybe_key:
        company, bind_error = await _bind_staff_by_api_key(
            api_key=maybe_key,
            max_user_id=max_user_id,
            max_username=max_username,
        )
        if bind_error:
            await send_max_message(user_id=max_user_id, text=f"❌ {bind_error}")
            return
        if company is not None:
            await send_max_message(
                user_id=max_user_id,
                text=(
                    f"✅ Готово! Этот чат подключён к уведомлениям компании "
                    f"«{company.name}». Здесь будут появляться новые записи."
                ),
            )
            return

    async with AsyncSessionLocal() as session:
        if await is_staff_max_user(session, max_user_id):
            await send_max_message(
                user_id=max_user_id,
                text="Вы подключены как сотрудник. Новые записи будут приходить сюда.",
            )
            return

    await _send_client_greeting(max_user_id, full_name)


async def _handle_contact(*, max_user_id: int, phone_raw: str) -> None:
    digits = _clean_phone(phone_raw)
    if not digits:
        await send_max_message(
            user_id=max_user_id,
            text="Не удалось прочитать номер телефона. Попробуйте ещё раз.",
        )
        return

    normalized = normalize_phone(digits) or digits

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Client, Company, Appointment)
                .join(Company, Client.company_id == Company.id)
                .outerjoin(
                    Appointment,
                    (Appointment.client_id == Client.id)
                    & (Appointment.status.notin_(_INACTIVE_STATUSES)),
                )
                .where(func.regexp_replace(Client.phone, r"[^0-9]", "", "g") == normalized)
                .order_by(Appointment.appointment_date.asc().nulls_last())
            )
            rows = result.all()

            clients_updated: set[uuid.UUID] = set()
            for client, _company, _appointment in rows:
                if client.id not in clients_updated:
                    client.max_user_id = max_user_id
                    if client.preferred_messenger in ("telegram", "", None):
                        client.preferred_messenger = "max"
                    clients_updated.add(client.id)

            await session.commit()

            active: list[tuple[Company, Appointment]] = []
            seen_appt: set[uuid.UUID] = set()
            for client, company, appointment in rows:
                if appointment is None or appointment.id in seen_appt:
                    continue
                seen_appt.add(appointment.id)
                active.append((company, appointment))

        if not clients_updated:
            await send_max_message(
                user_id=max_user_id,
                text=(
                    "По этому номеру записей пока нет. "
                    "Когда вы запишетесь — напоминания смогут приходить сюда в MAX."
                ),
            )
            return

        if not active:
            await send_max_message(
                user_id=max_user_id,
                text=(
                    "✅ Номер привязан к ICS. Активных записей сейчас нет — "
                    "напоминания о новых визитах будут приходить сюда."
                ),
            )
            return

        lines = ["Ваши актуальные записи:\n"]
        for company, appointment in active[:10]:
            date_s = appointment.appointment_date.strftime("%d.%m.%Y")
            time_s = appointment.appointment_time.strftime("%H:%M")
            lines.append(
                f"• {date_s} {time_s} — «{appointment.service_name}» в «{company.name}»"
            )
        await send_max_message(user_id=max_user_id, text="\n".join(lines))
    except Exception:  # noqa: BLE001
        logger.exception("Failed to handle MAX contact for user_id=%s", max_user_id)
        await send_max_message(
            user_id=max_user_id,
            text="Не удалось загрузить записи. Попробуйте позже.",
        )


async def _handle_confirm_callback(*, max_user_id: int, appointment_id: uuid.UUID) -> None:
    client_phone: str | None = None
    client_name: str | None = None
    company_name: str | None = None
    service_name: str | None = None
    appointment_date = None
    appointment_time = None
    company_id: uuid.UUID | None = None
    client_max_user_id: int | None = None

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Appointment, Client, Company)
                .join(Client, Appointment.client_id == Client.id)
                .join(Company, Appointment.company_id == Company.id)
                .where(Appointment.id == appointment_id)
            )
            row = result.first()
            if row is None:
                await send_max_message(
                    user_id=max_user_id,
                    text="Запись не найдена (возможно, уже удалена).",
                )
                return

            appointment, client, company = row

            staff_check = await session.execute(
                select(CompanyStaff).where(
                    CompanyStaff.company_id == appointment.company_id,
                    CompanyStaff.max_user_id == max_user_id,
                    CompanyStaff.is_active.is_(True),
                )
            )
            if staff_check.scalars().first() is None:
                await send_max_message(
                    user_id=max_user_id,
                    text="У вас нет прав подтверждать записи этой компании.",
                )
                return

            if appointment.status == AppointmentStatus.CONFIRMED:
                await send_max_message(
                    user_id=max_user_id,
                    text="Эта запись уже подтверждена.",
                )
                return

            appointment.status = AppointmentStatus.CONFIRMED
            await session.commit()

            client_phone = client.phone
            client_name = client.full_name
            company_name = company.name
            company_id = company.id
            service_name = appointment.service_name
            appointment_date = appointment.appointment_date
            appointment_time = appointment.appointment_time
            client_max_user_id = client.max_user_id
    except Exception:  # noqa: BLE001
        logger.exception("Failed to confirm appointment_id=%s via MAX", appointment_id)
        await send_max_message(
            user_id=max_user_id,
            text="Не удалось подтвердить запись. Попробуйте ещё раз позже.",
        )
        return

    await send_max_message(user_id=max_user_id, text="Запись успешно подтверждена ✅")

    if client_phone and appointment_date and appointment_time and company_id:
        context = build_appointment_context(
            client_name=client_name or "",
            company_name=company_name or "",
            service_name=service_name or "",
            appointment_date=appointment_date,
            appointment_time=appointment_time,
        )
        confirmation_text, enabled = await get_template_text(
            company_id, "booking_confirmed", context=context
        )
        if enabled and confirmation_text:
            try:
                await notify_client(
                    client_phone,
                    confirmation_text,
                    max_user_id=client_max_user_id,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Client notify failed after MAX confirm appointment_id=%s",
                    appointment_id,
                )


async def process_max_update(update: dict[str, Any]) -> None:
    """Dispatch a single MAX Update object."""
    update_type = update.get("update_type") or update.get("type") or ""
    max_user_id = _extract_user_id(update)
    if max_user_id is None:
        logger.warning("MAX update without user_id: type=%s keys=%s", update_type, list(update))
        return

    user = _extract_user(update) or {}
    max_username = _extract_username(update)
    full_name = user.get("name") or user.get("first_name")

    if update_type in ("bot_started", "bot_added"):
        # Deep-link payload may contain api_key in bot_started
        payload = update.get("payload")
        if isinstance(payload, str) and payload.strip():
            company, bind_error = await _bind_staff_by_api_key(
                api_key=payload.strip(),
                max_user_id=max_user_id,
                max_username=max_username,
            )
            if bind_error:
                await send_max_message(user_id=max_user_id, text=f"❌ {bind_error}")
                return
            if company is not None:
                await send_max_message(
                    user_id=max_user_id,
                    text=(
                        f"✅ Готово! Этот чат подключён к уведомлениям компании "
                        f"«{company.name}»."
                    ),
                )
                return

        async with AsyncSessionLocal() as session:
            if await is_staff_max_user(session, max_user_id):
                await send_max_message(
                    user_id=max_user_id,
                    text="Вы подключены как сотрудник. Новые записи будут приходить сюда.",
                )
                return
        await _send_client_greeting(max_user_id, full_name if isinstance(full_name, str) else None)
        return

    if update_type == "message_callback":
        payload = _extract_callback_payload(update) or ""
        if payload.startswith("confirm:"):
            raw_id = payload.split(":", 1)[1].strip()
            try:
                appointment_id = uuid.UUID(raw_id)
            except ValueError:
                await send_max_message(user_id=max_user_id, text="Некорректный идентификатор записи.")
                return
            await _handle_confirm_callback(max_user_id=max_user_id, appointment_id=appointment_id)
        return

    if update_type in ("message_created", "message"):
        phone = _extract_contact_phone(update)
        if phone:
            await _handle_contact(max_user_id=max_user_id, phone_raw=phone)
            return

        text = _extract_text(update)
        if not text:
            return
        await _handle_staff_or_client_text(
            max_user_id=max_user_id,
            text=text,
            max_username=max_username,
            full_name=full_name if isinstance(full_name, str) else None,
        )


@router.post("/max", status_code=status.HTTP_200_OK)
async def max_webhook(
    request: Request,
    x_max_bot_api_secret: str | None = Header(default=None, alias="X-Max-Bot-Api-Secret"),
) -> dict[str, str]:
    """Receive MAX Bot API webhook updates."""
    expected = (settings.MAX_WEBHOOK_SECRET or "").strip()
    if expected and (x_max_bot_api_secret or "").strip() != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from None

    updates: list[dict[str, Any]]
    if isinstance(payload, list):
        updates = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        if "updates" in payload and isinstance(payload["updates"], list):
            updates = [item for item in payload["updates"] if isinstance(item, dict)]
        else:
            updates = [payload]
    else:
        updates = []

    for update in updates:
        try:
            await process_max_update(update)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to process MAX update: %s", update.get("update_type"))

    return {"ok": "true"}
