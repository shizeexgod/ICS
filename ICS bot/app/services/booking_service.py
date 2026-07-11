"""Shared booking creation helpers for webhooks and admin cabinet."""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.models.company import Company
from app.services.scheduler import schedule_appointment_reminder
from app.services.staff_service import normalize_phone
from app.services.telegram_notifications import notify_company_managers_of_new_booking

logger = logging.getLogger(__name__)


async def get_or_create_client(
    session: AsyncSession, *, company_id: uuid.UUID, full_name: str, phone: str
) -> Client:
    """Fetch an existing client by phone (scoped to company) or create one."""
    normalized = normalize_phone(phone) or phone.strip()
    result = await session.execute(
        select(Client).where(
            Client.company_id == company_id,
            func.regexp_replace(Client.phone, r"[^0-9]", "", "g") == normalized,
        )
    )
    client = result.scalars().first()
    if client is not None:
        if client.full_name != full_name:
            client.full_name = full_name
        if client.phone != normalized:
            client.phone = normalized
        return client

    client = Client(company_id=company_id, full_name=full_name, phone=normalized)
    session.add(client)
    await session.flush()
    return client


async def create_company_appointment(
    session: AsyncSession,
    *,
    company: Company,
    full_name: str,
    phone: str,
    service_name: str,
    appointment_date: dt.date,
    appointment_time: dt.time,
    notify_telegram: bool = True,
    schedule_reminder: bool = True,
) -> tuple[Client, Appointment]:
    """Persist a new appointment and optionally notify managers + schedule reminder."""
    client = await get_or_create_client(
        session,
        company_id=company.id,
        full_name=full_name,
        phone=phone,
    )
    appointment = Appointment(
        company_id=company.id,
        client_id=client.id,
        service_name=service_name,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        status=AppointmentStatus.PENDING,
    )
    session.add(appointment)
    await session.commit()
    await session.refresh(appointment)
    await session.refresh(client)

    if notify_telegram:
        try:
            await notify_company_managers_of_new_booking(
                session,
                company_id=company.id,
                appointment_id=appointment.id,
                company_name=company.name,
                client_name=client.full_name,
                client_phone=client.phone,
                service_name=appointment.service_name,
                appointment_date=appointment.appointment_date,
                appointment_time=appointment.appointment_time,
            )
        except Exception:
            logger.exception(
                "Telegram notification failed for appointment_id=%s", appointment.id
            )

    if schedule_reminder:
        try:
            appointment_datetime = dt.datetime.combine(
                appointment.appointment_date, appointment.appointment_time
            )
            schedule_appointment_reminder(appointment.id, appointment_datetime)
        except Exception:
            logger.exception(
                "Failed to schedule reminder for appointment_id=%s", appointment.id
            )

    return client, appointment
