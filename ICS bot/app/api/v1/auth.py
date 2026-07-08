"""Email OTP authentication endpoints."""

from __future__ import annotations

import datetime as dt
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.db import supabase
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
    expires_at = email_code_expiry().isoformat()

    try:
        result = await (
            supabase.table("email_verifications")
            .upsert(
                {
                    "email": email,
                    "code": code,
                    "expires_at": expires_at,
                    "name": payload.name,
                    "phone": payload.phone,
                },
                on_conflict="email",
            )
            .execute_async()
        )
        if getattr(result, "data", None) is None and getattr(result, "error", None):
            logger.error("Supabase upsert failed for email=%s: %s", email, result.error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store verification code.",
            )
    except HTTPException:
        raise
    except Exception:
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
        result = await (
            supabase.table("email_verifications")
            .select("code", "expires_at", "name", "phone")
            .eq("email", email)
            .execute_async()
        )
        rows = result.data or []
    except Exception:
        logger.exception("Database error during verify-code lookup for email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed. Please try again later.",
        ) from None

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid code.",
        )

    record = rows[0]
    stored_code = record.get("code")
    expires_raw = record.get("expires_at")
    profile_name = record.get("name")
    profile_phone = record.get("phone")

    if stored_code != payload.code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid code.",
        )

    try:
        expires_at = dt.datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        logger.error("Malformed expires_at for email=%s: %r", email, expires_raw)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed. Please try again later.",
        ) from None

    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Code expired. Request a new one.",
        )

    try:
        user_result = await (
            supabase.table("users").select("*").eq("email", email).execute_async()
        )
        users = user_result.data or []
    except Exception:
        logger.exception("Database error while loading user email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed. Please try again later.",
        ) from None

    if users:
        user_row = users[0]
        try:
            await (
                supabase.table("users")
                .upsert(
                    {
                        "id": user_row["id"],
                        "email": email,
                        "name": profile_name or user_row.get("name"),
                        "phone": profile_phone or user_row.get("phone"),
                        "role": user_row.get("role") or "client",
                    },
                    on_conflict="email",
                )
                .execute_async()
            )
            user_result = await (
                supabase.table("users").select("*").eq("email", email).execute_async()
            )
            users = user_result.data or [user_row]
            user_row = users[0]
        except Exception:
            logger.exception("Failed to update profile for email=%s", email)
    else:
        try:
            await (
                supabase.table("users")
                .insert(
                    {
                        "email": email,
                        "name": profile_name,
                        "phone": profile_phone,
                        "role": "client",
                    }
                )
                .execute_async()
            )
            user_result = await (
                supabase.table("users").select("*").eq("email", email).execute_async()
            )
            users = user_result.data or []
            if not users:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to register user.",
                )
            user_row = users[0]
            logger.info("Registered new user email=%s id=%s", email, user_row.get("id"))
        except HTTPException:
            raise
        except Exception:
            logger.exception("Database error while registering user email=%s", email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register user.",
            ) from None

    try:
        await (
            supabase.table("email_verifications")
            .delete()
            .eq("email", email)
            .execute_async()
        )
    except Exception:
        logger.exception("Failed to delete used verification code for email=%s", email)

    user_id = uuid.UUID(str(user_row["id"]))
    role = str(user_row.get("role") or "client")
    access_token = create_access_token(user_id=user_id, email=email, role=role)
    refresh_token = create_refresh_token(user_id=user_id, email=email)

    user_out = UserOut(
        id=user_id,
        email=email,
        name=user_row.get("name"),
        phone=user_row.get("phone"),
        tg_chat_id=user_row.get("tg_chat_id"),
        company_id=(
            uuid.UUID(str(user_row["company_id"]))
            if user_row.get("company_id")
            else None
        ),
        role=role,
        created_at=user_row.get("created_at"),
    )

    logger.info("User authenticated email=%s user_id=%s", email, user_id)
    return VerifyCodeResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_out,
    )
