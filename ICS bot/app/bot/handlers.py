"""Telegram bot command, message, and callback-query handlers.

Covers three user flows:
1. Admin/manager onboarding: `/start <api_key>` (deep-link) or a plain message
   containing a valid company `api_key` binds the sender's chat to that company
   in `company_managers`, so future booking notifications reach them.
2. Client self-service: a plain `/start` (no args) greets the user and asks
   them to share their phone number via a Reply keyboard button; once shared,
   the bot looks up and lists their active appointments across all companies.
3. Admin actions: tapping "Подтвердить запись" on a booking card confirms the
   appointment in the DB and notifies the client via WhatsApp/SMS.
"""

from __future__ import annotations

import logging
import re
import uuid

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy import func, select

from app.bot.callbacks import ConfirmBookingCallback
from app.core.database import AsyncSessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.models.company import Company
from app.models.company_manager import CompanyManager
from app.services.notifications import notify_client

logger = logging.getLogger(__name__)

router = Router(name="main")

_DIGITS_ONLY_RE = re.compile(r"\D")

_INACTIVE_STATUSES = (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED)

_CONTACT_BUTTON_TEXT = "Мои записи"

_CLIENT_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=_CONTACT_BUTTON_TEXT, request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


def _clean_phone(phone: str) -> str:
    """Strip everything but digits from a phone number."""
    return _DIGITS_ONLY_RE.sub("", phone or "")


async def _bind_manager(*, api_key: str, tg_chat_id: int) -> Company | None:
    """Validate `api_key` against `companies` and upsert a `company_managers` row.

    Returns the matched `Company` on success, or `None` if the key is unknown.
    Idempotent: calling this again for the same (company, chat) pair is a no-op.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Company).where(Company.api_key == api_key))
        company = result.scalars().first()
        if company is None:
            return None

        existing = await session.execute(
            select(CompanyManager).where(
                CompanyManager.company_id == company.id,
                CompanyManager.tg_chat_id == tg_chat_id,
            )
        )
        if existing.scalars().first() is None:
            session.add(CompanyManager(company_id=company.id, tg_chat_id=tg_chat_id))
            await session.commit()
            logger.info(
                "Bound tg_chat_id=%s as manager of company_id=%s (%s)",
                tg_chat_id,
                company.id,
                company.name,
            )
        return company


async def _send_client_greeting(message: Message) -> None:
    """Greet a non-admin user and prompt them to share their phone number."""
    full_name = message.from_user.full_name if message.from_user else "друг"
    await message.answer(
        f"Привет, {full_name}! 👋\n"
        "Я бот сервиса онлайн-записи.\n\n"
        "Нажмите кнопку «Мои записи» ниже, чтобы поделиться номером телефона — "
        "я покажу ваши актуальные записи.",
        reply_markup=_CLIENT_KEYBOARD,
    )


@router.message(CommandStart())
async def handle_start(message: Message, command: CommandObject) -> None:
    """Handle `/start` with or without a deep-link/typed argument.

    `/start <api_key>` (e.g. via a `t.me/bot?start=<api_key>` deep link) attempts
    to bind the sender as a manager of that company. Plain `/start` shows the
    client-facing greeting with the "share contact" button instead.
    """
    tg_chat_id = message.chat.id
    maybe_api_key = (command.args or "").strip()

    if maybe_api_key:
        company = await _bind_manager(api_key=maybe_api_key, tg_chat_id=tg_chat_id)
        if company is not None:
            await message.answer(
                f"✅ Готово! Этот чат подключён к уведомлениям компании "
                f"«{company.name}». Здесь будут появляться новые записи."
            )
            return
        logger.info("Rejected admin bind attempt: unknown api_key in /start payload.")
        # Fall through to the client greeting — an invalid deep-link payload
        # shouldn't leave the user stuck with no response at all.

    await _send_client_greeting(message)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_plain_text(message: Message) -> None:
    """Treat a plain text message as a possible company `api_key` for admin binding.

    This lets a manager simply paste their company's API key into the chat
    instead of using a `/start <api_key>` deep link. Anything that doesn't
    match a known key is answered with a short hint.
    """
    text = (message.text or "").strip()
    if not text:
        return

    tg_chat_id = message.chat.id
    company = await _bind_manager(api_key=text, tg_chat_id=tg_chat_id)
    if company is not None:
        await message.answer(
            f"✅ Готово! Этот чат подключён к уведомлениям компании "
            f"«{company.name}». Здесь будут появляться новые записи."
        )
        return

    await message.answer(
        "Не удаётся распознать сообщение. Если вы администратор компании — "
        "отправьте свой API-ключ. Если вы клиент — нажмите /start и поделитесь "
        "номером телефона, чтобы посмотреть свои записи."
    )


@router.message(F.contact)
async def handle_contact(message: Message) -> None:
    """Look up and list a client's active appointments by their shared phone number."""
    contact = message.contact
    if contact is None or not contact.phone_number:
        await message.answer("Не удалось прочитать номер телефона. Попробуйте ещё раз.")
        return

    digits_only = _clean_phone(contact.phone_number)
    if not digits_only:
        await message.answer("Номер телефона выглядит некорректно. Попробуйте ещё раз.")
        return

    tg_user_id = message.from_user.id if message.from_user else None

    try:
        async with AsyncSessionLocal() as session:
            query = (
                select(Appointment, Client, Company)
                .join(Client, Appointment.client_id == Client.id)
                .join(Company, Appointment.company_id == Company.id)
                .where(func.regexp_replace(Client.phone, r"\D", "", "g") == digits_only)
                .where(Appointment.status.notin_(_INACTIVE_STATUSES))
                .order_by(Appointment.appointment_date, Appointment.appointment_time)
            )
            result = await session.execute(query)
            rows = result.all()

            if tg_user_id is not None:
                await session.execute(
                    Client.__table__.update()
                    .where(func.regexp_replace(Client.phone, r"\D", "", "g") == digits_only)
                    .values(tg_user_id=tg_user_id)
                )
                await session.commit()
    except Exception:  # noqa: BLE001 - never let a handler crash the dispatcher
        logger.exception("Failed to look up appointments for phone digits=%s", digits_only)
        await message.answer(
            "Не удалось загрузить ваши записи. Попробуйте ещё раз позже.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if not rows:
        await message.answer(
            "Активных записей не найдено.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    lines = ["📋 *Вы записаны:*", ""]
    for appointment, _client, company in rows:
        lines.append(
            f"📅 {appointment.appointment_date.strftime('%d.%m.%Y')} в "
            f"{appointment.appointment_time.strftime('%H:%M')} — "
            f"{appointment.service_name} в «{company.name}»"
        )

    await message.answer(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.callback_query(ConfirmBookingCallback.filter())
async def handle_confirm_appointment(
    callback: CallbackQuery, callback_data: ConfirmBookingCallback
) -> None:
    """Handle a tap on the "✅ Подтвердить запись" inline button."""
    appointment_id: uuid.UUID = callback_data.appointment_id
    logger.info(
        "Received 'confirm' callback for appointment_id=%s from tg_user_id=%s",
        appointment_id,
        callback.from_user.id if callback.from_user else None,
    )

    client_phone: str | None = None
    service_name: str | None = None
    appointment_date = None
    appointment_time = None

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Appointment, Client)
                .join(Client, Appointment.client_id == Client.id)
                .where(Appointment.id == appointment_id)
            )
            row = result.first()

            if row is None:
                await callback.answer("Запись не найдена (возможно, уже удалена).", show_alert=True)
                return

            appointment, client = row

            tg_chat_id = callback.message.chat.id if callback.message else None
            if tg_chat_id is not None:
                manager_check = await session.execute(
                    select(CompanyManager).where(
                        CompanyManager.company_id == appointment.company_id,
                        CompanyManager.tg_chat_id == tg_chat_id,
                    )
                )
                if manager_check.scalars().first() is None:
                    await callback.answer(
                        "У вас нет прав подтверждать записи этой компании.",
                        show_alert=True,
                    )
                    return

            if appointment.status == AppointmentStatus.CONFIRMED:
                await callback.answer("Эта запись уже подтверждена.", show_alert=False)
                return

            appointment.status = AppointmentStatus.CONFIRMED
            await session.commit()

            client_phone = client.phone
            service_name = appointment.service_name
            appointment_date = appointment.appointment_date
            appointment_time = appointment.appointment_time
    except Exception:  # noqa: BLE001 - never let a handler crash the dispatcher
        logger.exception(
            "Failed to confirm appointment_id=%s from callback.", appointment_id
        )
        await callback.answer(
            "Не удалось подтвердить запись. Попробуйте ещё раз позже.", show_alert=True
        )
        return

    await callback.answer("Запись подтверждена ✅")

    if callback.message is not None:
        try:
            await callback.message.edit_text(
                "Запись успешно подтверждена ✅",
                reply_markup=None,
            )
        except Exception:  # noqa: BLE001 - editing is best-effort, confirmation already saved
            logger.exception(
                "Confirmed appointment_id=%s but failed to edit the admin message.",
                appointment_id,
            )

    if client_phone and appointment_date and appointment_time:
        confirmation_text = (
            f"✅ Ваша запись на «{service_name}» "
            f"{appointment_date.strftime('%d.%m.%Y')} в {appointment_time.strftime('%H:%M')} "
            "подтверждена!"
        )
        try:
            await notify_client(client_phone, confirmation_text)
        except Exception:  # noqa: BLE001 - a broken client notification must not break the callback
            logger.exception(
                "Confirmed appointment_id=%s but failed to notify the client by "
                "WhatsApp/SMS.",
                appointment_id,
            )
