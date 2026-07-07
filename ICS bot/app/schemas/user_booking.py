"""Pydantic schemas for authenticated end-user booking endpoints."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel

from app.models.appointment import AppointmentStatus


class UserBookingItem(BaseModel):
    id: uuid.UUID
    service_name: str
    company_name: str
    appointment_date: dt.date
    appointment_time: dt.time
    status: AppointmentStatus


class CancelBookingResponse(BaseModel):
    ok: bool = True
    message: str = "Booking cancelled."
