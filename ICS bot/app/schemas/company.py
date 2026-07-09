"""Pydantic schemas for company onboarding and tenant profile."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.appointment import AppointmentListItem
from app.schemas.auth import UserOut

TRIAL_DAYS = 7
TRIAL_REMINDER_LIMIT = 100
PRO_PRICE_RUB = 5000


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


class CompanyTelegramOut(BaseModel):
    connected: bool
    managers: list[TelegramManagerOut]


class UserProfileUpdateRequest(BaseModel):
    phone: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, min_length=2, max_length=255)
