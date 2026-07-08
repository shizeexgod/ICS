"""Pydantic schemas for the company dashboard's appointments API."""

from __future__ import annotations

import datetime as dt
import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.appointment import AppointmentStatus

_PHONE_CLEANUP_RE = re.compile(r"[^\d+]")


class AppointmentListItem(BaseModel):
    """A single appointment row as returned by `GET /api/v1/appointments`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_name: str
    client_phone: str
    service_name: str
    appointment_date: dt.date
    appointment_time: dt.time
    status: AppointmentStatus


class AppointmentStatusUpdateRequest(BaseModel):
    """Request body for `PATCH /api/v1/appointments/{appointment_id}/status`.

    `status` is validated against `AppointmentStatus`, so an invalid value (e.g.
    a typo) is rejected automatically with a 422 before it ever reaches the DB.
    """

    status: AppointmentStatus


class AppointmentStatusUpdateResponse(BaseModel):
    """Response returned after successfully updating an appointment's status."""

    message: str = "Status updated successfully"


class AppointmentCreateRequest(BaseModel):
    """Create a booking from the admin calendar."""

    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=5, max_length=32)
    service_name: str = Field(..., min_length=1, max_length=255)
    appointment_date: dt.date
    appointment_time: dt.time

    @field_validator("full_name", "service_name")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be empty.")
        return value

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, value: str) -> str:
        cleaned = _PHONE_CLEANUP_RE.sub("", value.strip())
        if len(cleaned) < 5:
            raise ValueError("Phone number looks invalid.")
        return cleaned


class AppointmentCreateResponse(BaseModel):
    ok: bool = True
    appointment_id: uuid.UUID
    client_id: uuid.UUID
    message: str = "Appointment created successfully."
