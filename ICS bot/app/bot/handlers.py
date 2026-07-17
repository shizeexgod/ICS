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
from app.models.company_staff import CompanyStaff
from app.services.notifications import notify_client
from app.services.staff_service import bind_staff_chat, is_staff_chat
from app.services.template_service import build_appointment_context, get_template_text

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


async def _bind_manager(
    *,
    api_key: str,
    tg_chat_id: int,
    telegram_username: str | None = None,
) -> tuple[Company | None, str | None]:
    """Validate api_key and bind the chat to company staff.

    Returns (company, error_message). On success error_message is None.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Company).where(Company.api_key == api_key))
        company = result.scalars().first()
        if company is None:
            return None, None

        staff, error = await bind_staff_chat(
            session,
            company=company,
            tg_chat_id=tg_chat_id,
            telegram_username=telegram_username,
        )
        if error:
            return None, error

        logger.info(
            "Bound tg_chat_id=%s as staff of company_id=%s (%s), staff_id=%s",
            tg_chat_id,
            company.id,
            company.name,
            staff.id if staff else None,
        )
        return company, None


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
    tg_username = message.from_user.username if message.from_user else None

    if maybe_api_key:
        company, bind_error = await _bind_manager(
            api_key=maybe_api_key,
            tg_chat_id=tg_chat_id,
            telegram_username=tg_username,
        )
        if bind_error:
            await message.answer(f"❌ {bind_error}")
            return
        if company is not None:
            await message.answer(
                f"✅ Готово! Этот чат подключён к уведомлениям компании "
                f"«{company.name}». Здесь будут появляться новые записи."
            )
            return
        logger.info("Rejected admin bind attempt: unknown api_key in /start payload.")

    async with AsyncSessionLocal() as session:
        if await is_staff_chat(session, tg_chat_id):
            await message.answer(
                "Вы подключены как сотрудник. Новые записи будут приходить сюда."
            )
            return

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
    tg_username = message.from_user.username if message.from_user else None
    company, bind_error = await _bind_manager(
        api_key=text,
        tg_chat_id=tg_chat_id,
        telegram_username=tg_username,
    )
    if bind_error:
        await message.answer(f"❌ {bind_error}")
        return
    if company is not None:
        await message.answer(
            f"✅ Готово! Этот чат подключён к уведомлениям компании "
            f"«{company.name}». Здесь будут появляться новые записи."
        )
        return

    async with AsyncSessionLocal() as session:
        if await is_staff_chat(session, tg_chat_id):
            await message.answer(
                "Вы уже подключены как сотрудник. Новые записи будут приходить сюда."
            )
            return

    await message.answer(
        "Не удаётся распознать сообщение. Если вы сотрудник — отправьте API-ключ "
        "компании (его добавляет администратор в кабинете ICS). "
        "Если вы клиент — нажмите /start и поделитесь номером телефона."
    )


@router.message(F.contact)
async def handle_contact(message: Message) -> None:
    """Look up and list a client's active appointments by their shared phone number."""
    tg_chat_id = message.chat.id

    async with AsyncSessionLocal() as session:
        if await is_staff_chat(session, tg_chat_id):
            await message.answer(
                "Вы подключены как сотрудник компании. "
                "Клиентские записи доступны только клиентам через этот бот.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

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
                await callback.answer("Запись не найдена (возможно, уже удалена).", show_alert=True)
                return

            appointment, client, company = row

            tg_chat_id = callback.message.chat.id if callback.message else None
            if tg_chat_id is not None:
                staff_check = await session.execute(
                    select(CompanyStaff).where(
                        CompanyStaff.company_id == appointment.company_id,
                        CompanyStaff.tg_chat_id == tg_chat_id,
                        CompanyStaff.is_active.is_(True),
                    )
                )
                manager_check = await session.execute(
                    select(CompanyManager).where(
                        CompanyManager.company_id == appointment.company_id,
                        CompanyManager.tg_chat_id == tg_chat_id,
                    )
                )
                if staff_check.scalars().first() is None and manager_check.scalars().first() is None:
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
            client_name = client.full_name
            company_name = company.name
            company_id = company.id
            service_name = appointment.service_name
            appointment_date = appointment.appointment_date
            appointment_time = appointment.appointment_time
            client_max_user_id = client.max_user_id
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
        if not enabled or not confirmation_text:
            return
        try:
            await notify_client(
                client_phone,
                confirmation_text,
                max_user_id=client_max_user_id,
            )
        except Exception:  # noqa: BLE001 - a broken client notification must not break the callback
            logger.exception(
                "Confirmed appointment_id=%s but failed to notify the client by "
                "WhatsApp/SMS/MAX.",
                appointment_id,
            )
