"""Email OTP generation and JWT token helpers."""

from __future__ import annotations

import datetime as dt
import logging
import secrets
import uuid

import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

EMAIL_CODE_LENGTH = 4
EMAIL_CODE_TTL_MINUTES = 5
REFRESH_TOKEN_DAYS = 30


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_email_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(EMAIL_CODE_LENGTH))


def email_code_expiry() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=EMAIL_CODE_TTL_MINUTES)


def create_access_token(*, user_id: uuid.UUID, email: str, role: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + dt.timedelta(days=settings.JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(*, user_id: uuid.UUID, email: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "refresh",
        "iat": now,
        "exp": now + dt.timedelta(days=REFRESH_TOKEN_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") not in (None, "access"):
        raise jwt.InvalidTokenError("Not an access token.")
    return payload


def decode_refresh_token(token: str) -> dict:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Not a refresh token.")
    return payload
