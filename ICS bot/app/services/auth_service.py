"""OTP generation/verification and JWT token helpers."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import logging
import secrets
import uuid

import jwt

from app.core.config import settings
from app.services.notifications import clean_phone_number, send_client_sms

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_TTL_MINUTES = 10


def normalize_phone(phone: str) -> str:
    return clean_phone_number(phone)


def generate_otp() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))


def hash_otp(otp: str) -> str:
    pepper = settings.JWT_SECRET or "ics-dev-secret"
    return hashlib.sha256(f"{otp}:{pepper}".encode()).hexdigest()


def verify_otp(otp: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    return hmac.compare_digest(hash_otp(otp), stored_hash)


def otp_expiry() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=OTP_TTL_MINUTES)


def create_access_token(*, user_id: uuid.UUID, phone: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "phone": phone,
        "iat": now,
        "exp": now + dt.timedelta(days=settings.JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


async def send_otp_sms(phone: str, otp: str) -> None:
    message = f"Код входа ICS: {otp}. Действует {OTP_TTL_MINUTES} мин."
    sent = await send_client_sms(phone, message)
    if not sent:
        logger.warning("OTP SMS may not have been delivered to phone=%s", normalize_phone(phone))

    if settings.ENVIRONMENT == "local":
        logger.info("[DEV OTP] phone=%s code=%s", normalize_phone(phone), otp)
