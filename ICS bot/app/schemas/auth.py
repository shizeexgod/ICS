"""Pydantic v2 schemas for email OTP authentication."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

_CODE_RE = re.compile(r"^\d{4}$")
_PHONE_CLEANUP_RE = re.compile(r"[^\d+]")


class SendCodeRequest(BaseModel):
    email: EmailStr
    # Optional: the "Войти" (login) flow only sends email for returning users,
    # who already have a name on file. "Регистрация" still sends it.
    name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    intent: Literal["login", "register"] = "login"

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) < 2:
            raise ValueError("Name must be at least 2 characters.")
        return value

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = _PHONE_CLEANUP_RE.sub("", value.strip())
        return cleaned or None


# Backward-compatible alias
EmailRequest = SendCodeRequest


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=4)

    @field_validator("code")
    @classmethod
    def _four_digits(cls, value: str) -> str:
        digits = value.strip()
        if not _CODE_RE.fullmatch(digits):
            raise ValueError("Code must be exactly 4 digits.")
        return digits


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None = None
    phone: str | None = None
    tg_chat_id: str | None = None
    company_id: uuid.UUID | None = None
    role: str
    created_at: datetime | None = None


class SendCodeResponse(BaseModel):
    ok: bool = True
    message: str = "Verification code sent to your email."
    dev_code: str | None = Field(
        default=None,
        description="Returned only in local dev when SMTP is not configured.",
    )


class VerifyCodeResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
