"""Pydantic schemas for company onboarding and tenant profile."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.appointment import AppointmentListItem
from app.schemas.auth import UserOut

TRIAL_DAYS = 10
TRIAL_REMINDER_LIMIT = 100

PLAN_PRICING: dict[str, dict[str, int]] = {
    "pro": {"monthly": 1490, "annual": 13900},
    "max": {"monthly": 2690, "annual": 22900},
}
BILLING_PERIOD_DAYS: dict[str, int] = {"monthly": 30, "annual": 365}

# Backward-compat default (display fallback when a company has no plan/period yet).
PRO_PRICE_RUB = PLAN_PRICING["pro"]["monthly"]


class CompanySetupRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    owner_email: EmailStr | None = None

    @field_validator("company_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Company name must not be empty.")
        return value


class CompanyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    owner_email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Company name must not be empty.")
        return value


class CompanyPlanOut(BaseModel):
    plan: str
    trial_ends_at: datetime | None = None
    subscription_status: str
    billing_period: str | None = None
    subscription_ends_at: datetime | None = None
    reminders_used: int
    reminders_limit: int | None = None
    reminders_remaining: int | None = None
    trial_days_left: int | None = None
    pro_price_rub: int
    is_trial_active: bool
    can_send_reminders: bool


class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    owner_email: str
    api_key: str
    created_at: datetime
    plan: CompanyPlanOut


class CompanySetupResponse(BaseModel):
    company: CompanyOut
    user: UserOut
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CompanyStatsOut(BaseModel):
    appointments_today: int
    active_clients: int
    reminders_week: int


class TelegramManagerOut(BaseModel):
    tg_chat_id: int
    full_name: str | None = None
    telegram_username: str | None = None
    role: str | None = None


class CompanyTelegramOut(BaseModel):
    connected: bool
    managers: list[TelegramManagerOut]
    staff_required: bool = False


class StaffOut(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str | None = None
    telegram_username: str | None = None
    role: str
    notify_bookings: bool
    tg_chat_id: int | None = None
    is_active: bool
    is_connected: bool = False
    created_at: datetime


class StaffCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    telegram_username: str | None = Field(default=None, max_length=64)
    role: str = Field(default="employee", max_length=32)
    notify_bookings: bool = True

    @field_validator("full_name")
    @classmethod
    def _strip_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name must not be empty.")
        return value

    @field_validator("telegram_username")
    @classmethod
    def _normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lstrip("@").lower()
        return value or None

    @field_validator("phone")
    @classmethod
    def _strip_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class StaffUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    telegram_username: str | None = Field(default=None, max_length=64)
    role: str | None = Field(default=None, max_length=32)
    notify_bookings: bool | None = None
    is_active: bool | None = None

    @field_validator("full_name")
    @classmethod
    def _strip_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Full name must not be empty.")
        return value

    @field_validator("telegram_username")
    @classmethod
    def _normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lstrip("@").lower()
        return value or None

    @field_validator("phone")
    @classmethod
    def _strip_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class UserProfileUpdateRequest(BaseModel):
    phone: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, min_length=2, max_length=255)
