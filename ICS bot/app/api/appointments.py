"""Company-dashboard REST API for listing and managing appointments."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_company
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.company import Company
from app.schemas.appointment import (
    AppointmentListItem,
    AppointmentStatusUpdateRequest,
    AppointmentStatusUpdateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentListItem])
async def list_appointments(
    company: Company = Depends(get_current_company),
    session: AsyncSession = Depends(get_db_session),
) -> list[AppointmentListItem]:
    """
    Return every appointment belonging to the authenticated company.

    Auth: pass the company's API key either via the `X-API-Key` header (any
    letter casing), the `api_key` query parameter, or an `api_key` JSON body field.
    """
    try:
        query = (
            select(Appointment, Client)
            .join(Client, Appointment.client_id == Client.id)
            .where(Appointment.company_id == company.id)
            .order_by(Appointment.appointment_date, Appointment.appointment_time)
        )
        result = await session.execute(query)
        rows = result.all()
    except Exception:
        logger.exception(
            "Database error while listing appointments for company_id=%s", company.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load appointments. Please try again later.",
        ) from None

    return [
        AppointmentListItem(
            id=appointment.id,
            client_name=client.full_name,
            client_phone=client.phone,
            service_name=appointment.service_name,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            status=appointment.status,
        )
        for appointment, client in rows
    ]


@router.patch("/{appointment_id}/status", response_model=AppointmentStatusUpdateResponse)
async def update_appointment_status(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdateRequest,
    company: Company = Depends(get_current_company),
    session: AsyncSession = Depends(get_db_session),
) -> AppointmentStatusUpdateResponse:
    """
    Update the status of a single appointment (e.g. to "confirmed" or "cancelled").

    The appointment must belong to the authenticated company; otherwise (or if it
    doesn't exist at all) a 404 is returned, never leaking other companies' data.
    """
    try:
        result = await session.execute(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.company_id == company.id,
            )
        )
        appointment = result.scalars().first()

        if appointment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found.",
            )

        appointment.status = payload.status
        await session.commit()
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Database error while updating status of appointment_id=%s for company_id=%s",
            appointment_id,
            company.id,
        )
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update the appointment status. Please try again later.",
        ) from None

    return AppointmentStatusUpdateResponse()
