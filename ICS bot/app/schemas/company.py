"""Pydantic schemas for company onboarding and tenant profile."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import UserOut


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


class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    owner_email: str
    api_key: str
    created_at: datetime


class CompanySetupResponse(BaseModel):
    company: CompanyOut
    user: UserOut
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
