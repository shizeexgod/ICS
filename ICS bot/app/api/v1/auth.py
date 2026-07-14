"""Email OTP authentication endpoints."""

from __future__ import annotations

import datetime as dt
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.email_verification import EmailVerification
from app.models.user import User
from app.schemas.auth import (
    SendCodeRequest,
    SendCodeResponse,
    UserOut,
    VerifyCodeRequest,
    VerifyCodeResponse,
)
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    email_code_expiry,
    generate_email_code,
    normalize_email,
)
from app.services.email import send_verification_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/send-code", response_model=SendCodeResponse)
@router.post("/register", response_model=SendCodeResponse, include_in_schema=True)
async def send_code(payload: SendCodeRequest) -> SendCodeResponse:
    """Generate a 4-digit code, store profile draft, and email the code."""
    email = normalize_email(str(payload.email))
    code = generate_email_code()
    expires_at = email_code_expiry()

    try:
        async with AsyncSessionLocal() as session:
            if payload.intent == "register":
                existing = await session.execute(select(User).where(User.email == email))
                if existing.scalar_one_or_none() is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Email already registered.",
                    )

            stmt = (
                insert(EmailVerification)
                .values(
                    email=email,
                    code=code,
                    expires_at=expires_at,
                    name=payload.name,
                    phone=payload.phone,
                )
                .on_conflict_do_update(
                    index_elements=[EmailVerification.email],
                    set_={
                        "code": code,
                        "expires_at": expires_at,
                        "name": payload.name,
                        "phone": payload.phone,
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()
    except SQLAlchemyError:
        logger.exception("Database error during send-code for email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store verification code.",
        ) from None

    smtp_configured = all(
        os.getenv(key) for key in ("SMTP_SERVER", "SMTP_USER", "SMTP_PASSWORD")
    )
    dev_code: str | None = None

    if smtp_configured:
        sent = await send_verification_email(email, code)
        if not sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email.",
            )
    elif settings.ENVIRONMENT == "local":
        dev_code = code
        logger.info("[DEV EMAIL CODE] email=%s code=%s", email, code)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email delivery is not configured.",
        )

    logger.info("Verification code issued for email=%s", email)
    return SendCodeResponse(dev_code=dev_code)


@router.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_code(payload: VerifyCodeRequest) -> VerifyCodeResponse:
    """Validate the emailed code, register or log in the user, return JWT tokens."""
    email = normalize_email(str(payload.email))
    now = dt.datetime.now(dt.timezone.utc)

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(EmailVerification).where(EmailVerification.email == email)
            )
            record = result.scalar_one_or_none()
            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid code.",
                )

            if record.code != payload.code:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid code.",
                )

            expires_at = record.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt.timezone.utc)

            if expires_at < now:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Code expired. Request a new one.",
                )

            profile_name = record.name
            profile_phone = record.phone

            user_result = await session.execute(select(User).where(User.email == email))
            user = user_result.scalar_one_or_none()

            if user is None:
                user = User(
                    email=email,
                    name=profile_name,
                    phone=profile_phone,
                    role="client",
                )
                session.add(user)
                await session.flush()
                logger.info("Registered new user email=%s id=%s", email, user.id)
            else:
                if profile_name:
                    user.name = profile_name
                if profile_phone:
                    user.phone = profile_phone

            await session.delete(record)
            await session.commit()
            await session.refresh(user)
    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Database error during verify-code for email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed. Please try again later.",
        ) from None

    access_token = create_access_token(user_id=user.id, email=email, role=user.role)
    refresh_token = create_refresh_token(user_id=user.id, email=email)

    user_out = UserOut(
        id=user.id,
        email=email,
        name=user.name,
        phone=user.phone,
        tg_chat_id=user.tg_chat_id,
        company_id=user.company_id,
        role=user.role,
        created_at=user.created_at,
    )

    logger.info("User authenticated email=%s user_id=%s", email, user.id)
    return VerifyCodeResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_out,
    )
