"""OTP-based authentication endpoints for the personal cabinet."""

from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, VerifyRequest, VerifyResponse
from app.core.config import settings
from app.services.auth_service import (
    generate_otp,
    hash_otp,
    normalize_phone,
    otp_expiry,
    send_otp_sms,
    verify_otp,
    create_access_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login_send_otp(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    """Send a one-time code to the user's phone (creates/updates the user row)."""
    phone = normalize_phone(payload.phone)
    otp = generate_otp()
    hashed = hash_otp(otp)
    expires = otp_expiry()

    try:
        result = await session.execute(select(User).where(User.phone == phone))
        user = result.scalars().first()

        if user is None:
            user = User(phone=phone, name=payload.name)
            session.add(user)
        else:
            user.name = payload.name

        user.otp_secret = hashed
        user.otp_expires_at = expires
        await session.commit()
    except Exception:
        logger.exception("Failed to upsert user for phone=%s during login.", phone)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start login. Please try again later.",
        ) from None

    await send_otp_sms(phone, otp)
    logger.info("OTP issued for user phone=%s", phone)

    dev_code: str | None = None
    if settings.ENVIRONMENT == "local" and not settings.SMS_RU_API_KEY:
        dev_code = otp

    return LoginResponse(dev_code=dev_code)


@router.post("/verify", response_model=VerifyResponse)
async def verify_otp_and_issue_token(
    payload: VerifyRequest,
    session: AsyncSession = Depends(get_db_session),
) -> VerifyResponse:
    """Verify the OTP code and return a JWT access token."""
    phone = normalize_phone(payload.phone)

    try:
        result = await session.execute(select(User).where(User.phone == phone))
        user = result.scalars().first()
    except Exception:
        logger.exception("Database error during OTP verify for phone=%s", phone)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed. Please try again later.",
        ) from None

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid code.")

    now = dt.datetime.now(dt.timezone.utc)
    expires_at = user.otp_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=dt.timezone.utc)

    if expires_at is None or expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Code expired. Request a new one.",
        )

    if not verify_otp(payload.code, user.otp_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid code.")

    user.otp_secret = None
    user.otp_expires_at = None
    await session.commit()

    token = create_access_token(user_id=user.id, phone=user.phone)
    logger.info("User authenticated phone=%s user_id=%s", phone, user.id)
    return VerifyResponse(access_token=token, name=user.name, phone=user.phone)
