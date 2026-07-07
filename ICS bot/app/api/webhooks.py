"""FastAPI webhook endpoints consumed by the frontend website (Tilda, etc.)."""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.models.company import Company
from app.schemas.booking import BookingResponse, TildaBookingPayload
from app.services.scheduler import schedule_appointment_reminder
from app.services.telegram_notifications import notify_company_managers_of_new_booking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post(
    "/tilda",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking_from_tilda(
    request: Request,
    payload: TildaBookingPayload,
    session: AsyncSession = Depends(get_db_session),
) -> BookingResponse:
    """
    Receive a booking submitted on the website, persist it, and notify Telegram.

    Expects a JSON body with `full_name`, `phone`, `service_name`, `appointment_date`,
    `appointment_time` fields, plus an API key supplied either via the `X-API-Key`
    header (in any letter case) or the `api_key` field in the JSON body.
    """
    api_key = await _extract_api_key(request)
    if not api_key:
        logger.warning("Rejected webhook request: no API key provided.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )

    company = await _get_company_by_api_key(session, api_key=api_key)
    if company is None:
        logger.warning("Rejected webhook request: unknown API key.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )

    try:
        client = await _get_or_create_client(
            session,
            company_id=company.id,
            full_name=payload.full_name,
            phone=payload.phone,
        )

        appointment = Appointment(
            company_id=company.id,
            client_id=client.id,
            service_name=payload.service_name,
            appointment_date=payload.appointment_date,
            appointment_time=payload.appointment_time,
            status=AppointmentStatus.PENDING,
        )
        session.add(appointment)
        await session.commit()
        await session.refresh(appointment)
        await session.refresh(client)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Failed to persist booking for company_id=%s phone=%s",
            company.id,
            payload.phone,
        )
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the booking. Please try again later.",
        ) from None

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

    try:
        appointment_datetime = dt.datetime.combine(
            appointment.appointment_date, appointment.appointment_time
        )
        schedule_appointment_reminder(appointment.id, appointment_datetime)
    except Exception:  # noqa: BLE001 - a scheduling failure must not fail the booking
        logger.exception(
            "Failed to schedule a reminder for appointment_id=%s", appointment.id
        )

    return BookingResponse(client_id=client.id, appointment_id=appointment.id, ok=True)


async def _extract_api_key(request: Request) -> str | None:
    """Extract the API key from the raw JSON body or the `X-API-Key` header."""
    api_key: str | None = None

    try:
        body: dict = await request.json()
    except Exception:  # noqa: BLE001 - malformed/empty body must not crash key extraction
        logger.exception("Failed to parse raw JSON body while extracting api_key.")
        body = {}

    if isinstance(body, dict):
        raw_value = body.get("api_key")
        if isinstance(raw_value, str) and raw_value.strip():
            api_key = raw_value.strip()

    if not api_key:
        for header_name in ("X-API-Key", "x-api-key", "X-Api-Key"):
            value = request.headers.get(header_name)
            if value and value.strip():
                api_key = value.strip()
                break

    return api_key or None


async def _get_company_by_api_key(session: AsyncSession, *, api_key: str) -> Company | None:
    """Look up a company by its per-tenant API key."""
    try:
        result = await session.execute(select(Company).where(Company.api_key == api_key))
        return result.scalars().first()
    except Exception:
        logger.exception("Database error while looking up company by API key.")
        raise


async def _get_or_create_client(
    session: AsyncSession, *, company_id: uuid.UUID, full_name: str, phone: str
) -> Client:
    """Fetch an existing client (scoped to the company) by phone number, or create a new one."""
    try:
        result = await session.execute(
            select(Client).where(Client.company_id == company_id, Client.phone == phone)
        )
        client = result.scalars().first()
    except Exception:
        logger.exception(
            "Database error while looking up client for company_id=%s phone=%s",
            company_id,
            phone,
        )
        raise

    if client is not None:
        if client.full_name != full_name:
            client.full_name = full_name
        return client

    client = Client(company_id=company_id, full_name=full_name, phone=phone)
    session.add(client)
    await session.flush()
    return client
