"""Authenticated end-user booking endpoints (personal cabinet)."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.models.company import Company
from app.models.user import User
from app.schemas.user_booking import CancelBookingResponse, UserBookingItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])

_INACTIVE = (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED)


@router.get("/my", response_model=list[UserBookingItem])
async def list_my_bookings(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[UserBookingItem]:
    """Return active appointments for the authenticated user (matched by email)."""
    user_email = user.email.strip().lower()
    if not user_email:
        return []

    try:
        query = (
            select(Appointment, Client, Company)
            .join(Client, Appointment.client_id == Client.id)
            .join(Company, Appointment.company_id == Company.id)
            .where(func.lower(Client.email) == user_email)
            .where(Appointment.status.notin_(_INACTIVE))
            .order_by(Appointment.appointment_date, Appointment.appointment_time)
        )
        result = await session.execute(query)
        rows = result.all()
    except Exception:
        logger.exception("Failed to load bookings for user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load bookings.",
        ) from None

    return [
        UserBookingItem(
            id=appointment.id,
            service_name=appointment.service_name,
            company_name=company.name,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            status=appointment.status,
        )
        for appointment, _client, company in rows
    ]


@router.post("/{appointment_id}/cancel", response_model=CancelBookingResponse)
async def cancel_my_booking(
    appointment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CancelBookingResponse:
    """Cancel an appointment that belongs to the authenticated user."""
    user_email = user.email.strip().lower()

    try:
        result = await session.execute(
            select(Appointment, Client)
            .join(Client, Appointment.client_id == Client.id)
            .where(Appointment.id == appointment_id)
            .where(func.lower(Client.email) == user_email)
        )
        row = result.first()
    except Exception:
        logger.exception(
            "Database error while cancelling appointment_id=%s for user_id=%s",
            appointment_id,
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel booking.",
        ) from None

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    appointment, _client = row
    if appointment.status in _INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already inactive.",
        )

    appointment.status = AppointmentStatus.CANCELLED
    await session.commit()
    logger.info("User user_id=%s cancelled appointment_id=%s", user.id, appointment_id)
    return CancelBookingResponse()
