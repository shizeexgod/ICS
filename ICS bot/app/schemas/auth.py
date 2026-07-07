"""Pydantic schemas for OTP login / JWT auth."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

_PHONE_CLEANUP_RE = re.compile(r"[^\d+]")


class LoginRequest(BaseModel):
    """Request OTP code for the given phone number."""

    phone: str = Field(..., min_length=5, max_length=32)
    name: str = Field(..., min_length=2, max_length=255)

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, value: str) -> str:
        cleaned = _PHONE_CLEANUP_RE.sub("", value.strip())
        if len(cleaned) < 5:
            raise ValueError("Phone number looks invalid.")
        return cleaned

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be empty.")
        return value


class LoginResponse(BaseModel):
    ok: bool = True
    message: str = "OTP sent."
    dev_code: str | None = Field(
        default=None,
        description="Returned only in local dev when SMS is not configured.",
    )


class VerifyRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=32)
    code: str = Field(..., min_length=4, max_length=6)

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, value: str) -> str:
        cleaned = _PHONE_CLEANUP_RE.sub("", value.strip())
        if len(cleaned) < 5:
            raise ValueError("Phone number looks invalid.")
        return cleaned

    @field_validator("code")
    @classmethod
    def _digits_only(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value.strip())
        if len(digits) < 4:
            raise ValueError("OTP code looks invalid.")
        return digits


class VerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    phone: str
