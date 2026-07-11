"""Helpers for company staff registration and Telegram binding."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.company_manager import CompanyManager
from app.models.company_staff import CompanyStaff

_DIGITS_ONLY_RE = re.compile(r"\D")


def normalize_username(username: str | None) -> str | None:
    if not username:
        return None
    value = username.strip().lstrip("@").lower()
    return value or None


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = _DIGITS_ONLY_RE.sub("", phone)
    return digits or None


def staff_out(staff: CompanyStaff) -> dict:
    return {
        "id": staff.id,
        "full_name": staff.full_name,
        "phone": staff.phone,
        "telegram_username": staff.telegram_username,
        "role": staff.role,
        "notify_bookings": staff.notify_bookings,
        "tg_chat_id": staff.tg_chat_id,
        "is_active": staff.is_active,
        "is_connected": staff.tg_chat_id is not None,
        "created_at": staff.created_at,
    }


async def company_has_active_staff(session: AsyncSession, company_id: uuid.UUID) -> bool:
    result = await session.execute(
        select(func.count(CompanyStaff.id)).where(
            CompanyStaff.company_id == company_id,
            CompanyStaff.is_active.is_(True),
        )
    )
    return (result.scalar() or 0) > 0


async def find_staff_for_binding(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    tg_chat_id: int,
    telegram_username: str | None,
) -> CompanyStaff | None:
    """Match a Telegram user to a pre-registered staff row for this company."""
    bound = await session.execute(
        select(CompanyStaff).where(
            CompanyStaff.company_id == company_id,
            CompanyStaff.tg_chat_id == tg_chat_id,
            CompanyStaff.is_active.is_(True),
        )
    )
    existing = bound.scalars().first()
    if existing is not None:
        return existing

    username = normalize_username(telegram_username)
    if username:
        by_username = await session.execute(
            select(CompanyStaff).where(
                CompanyStaff.company_id == company_id,
                func.lower(CompanyStaff.telegram_username) == username,
                CompanyStaff.is_active.is_(True),
            )
        )
        match = by_username.scalars().first()
        if match is not None:
            return match

    return None


async def bind_staff_chat(
    session: AsyncSession,
    *,
    company: Company,
    tg_chat_id: int,
    telegram_username: str | None,
) -> tuple[CompanyStaff | None, str | None]:
    """Bind a Telegram chat to company staff.

    Returns (staff, error_message). On success error_message is None.
    """
    staff_required = await company_has_active_staff(session, company.id)

    staff = await find_staff_for_binding(
        session,
        company_id=company.id,
        tg_chat_id=tg_chat_id,
        telegram_username=telegram_username,
    )

    if staff_required and staff is None:
        return None, (
            "Вы не в списке сотрудников этой компании. "
            "Попросите администратора добавить ваш Telegram @username в кабинете ICS."
        )

    if staff is None:
        staff = CompanyStaff(
            company_id=company.id,
            full_name=normalize_username(telegram_username) or f"Сотрудник {tg_chat_id}",
            telegram_username=normalize_username(telegram_username),
            role="employee",
        )
        session.add(staff)
        await session.flush()

    staff.tg_chat_id = tg_chat_id
    if telegram_username and not staff.telegram_username:
        staff.telegram_username = normalize_username(telegram_username)

    manager = await session.execute(
        select(CompanyManager).where(
            CompanyManager.company_id == company.id,
            CompanyManager.tg_chat_id == tg_chat_id,
        )
    )
    if manager.scalars().first() is None:
        session.add(CompanyManager(company_id=company.id, tg_chat_id=tg_chat_id))

    await session.commit()
    await session.refresh(staff)
    return staff, None


async def is_staff_chat(session: AsyncSession, tg_chat_id: int) -> bool:
    result = await session.execute(
        select(func.count(CompanyStaff.id)).where(
            CompanyStaff.tg_chat_id == tg_chat_id,
            CompanyStaff.is_active.is_(True),
        )
    )
    return (result.scalar() or 0) > 0


async def get_notification_chat_ids(session: AsyncSession, company_id: uuid.UUID) -> list[int]:
    """Return chat ids that should receive new-booking Telegram notifications."""
    staff_result = await session.execute(
        select(CompanyStaff.tg_chat_id).where(
            CompanyStaff.company_id == company_id,
            CompanyStaff.is_active.is_(True),
            CompanyStaff.notify_bookings.is_(True),
            CompanyStaff.tg_chat_id.is_not(None),
        )
    )
    chat_ids = list(staff_result.scalars().all())

    if chat_ids:
        return chat_ids

    legacy = await session.execute(
        select(CompanyManager.tg_chat_id).where(CompanyManager.company_id == company_id)
    )
    return list(legacy.scalars().all())
