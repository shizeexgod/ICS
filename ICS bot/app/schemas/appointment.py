"""Pydantic schemas for the company dashboard's appointments API."""

from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.appointment import AppointmentStatus


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
