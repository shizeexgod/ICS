"""Pydantic v2 schemas for email OTP authentication."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

_CODE_RE = re.compile(r"^\d{4}$")


class EmailRequest(BaseModel):
    email: EmailStr


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
