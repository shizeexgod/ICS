"""Pydantic schemas for the Tilda booking webhook."""

from __future__ import annotations

import datetime as dt
import re
import uuid

from pydantic import BaseModel, Field, field_validator

_PHONE_CLEANUP_RE = re.compile(r"[^\d+]")


class TildaBookingPayload(BaseModel):
    """Raw booking payload sent by the frontend website (e.g. a Tilda form).

    The `api_key` field is optional here because the key may instead be supplied
    via the `X-API-Key` HTTP header; the endpoint accepts either.
    """

    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=5, max_length=32)
    service_name: str = Field(..., min_length=1, max_length=255)
    appointment_date: dt.date
    appointment_time: dt.time
    api_key: str | None = Field(default=None)

    model_config = {"populate_by_name": True}

    @field_validator("full_name")
    @classmethod
    def _strip_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("full_name must not be empty.")
        return value

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, value: str) -> str:
        cleaned = _PHONE_CLEANUP_RE.sub("", value.strip())
        if len(cleaned) < 5:
            raise ValueError("Phone number looks invalid.")
        return cleaned

    @field_validator("service_name")
    @classmethod
    def _strip_service_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("service_name must not be empty.")
        return value

    @field_validator("api_key")
    @classmethod
    def _strip_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BookingResponse(BaseModel):
    """Response returned to the website after a successful booking.

    `client_id`/`appointment_id` are UUIDs, matching the real primary key type
    used by the `clients`/`appointments` tables in Supabase.
    """

    ok: bool
    client_id: uuid.UUID
    appointment_id: uuid.UUID
    message: str = "Appointment created successfully."
