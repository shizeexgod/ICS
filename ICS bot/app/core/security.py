"""Shared API-key extraction/authentication helpers for all `/api/*` and `/webhook/*` routes."""

from __future__ import annotations

import logging
import uuid

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.company import Company
from app.models.user import User
from app.services.auth_service import decode_access_token

logger = logging.getLogger(__name__)


async def extract_api_key(request: Request) -> str | None:
    """Extract the API key from the request, tolerant of every common transport.

    Priority order:
    1. The raw JSON body's `api_key` field (parsed directly, bypassing Pydantic,
       so validation quirks can never swallow/rename it). Safe to call even for
       requests with no body (e.g. GET) — a parse failure is treated as "absent".
    2. The `X-API-Key` header, probed in several common letter-casings.
    3. The `api_key` query parameter (handy for simple GET requests from a
       frontend dashboard where setting a custom header is inconvenient).
    """
    api_key: str | None = None

    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - no/invalid JSON body is expected for GET requests
        body = None

    if isinstance(body, dict):
        raw_value = body.get("api_key")
        if isinstance(raw_value, str) and raw_value.strip():
            api_key = raw_value.strip()

    if not api_key:
        for header_name in ("X-API-Key", "x-api-key", "X-Api-Key"):
            value = request.headers.get(header_name)
            if value and value.strip():
                api_key = value.strip()
                break

    if not api_key:
        query_value = request.query_params.get("api_key")
        if query_value and query_value.strip():
            api_key = query_value.strip()

    return api_key or None


async def get_company_by_api_key(session: AsyncSession, *, api_key: str) -> Company | None:
    """Look up a company by its API key. No hidden filters are applied."""
    try:
        result = await session.execute(select(Company).where(Company.api_key == api_key))
        return result.scalars().first()
    except Exception:
        logger.exception("Database error while looking up company by API key.")
        raise


async def get_current_company(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Company:
    """FastAPI dependency: resolve and return the `Company` for the caller's API key.

    Raises HTTP 401 if the key is missing from the request or doesn't match any
    company. Use this as a `Depends(...)` on any authenticated endpoint.
    """
    api_key = await extract_api_key(request)
    if not api_key:
        logger.warning("Rejected request to %s: no API key provided.", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )

    company = await get_company_by_api_key(session, api_key=api_key)
    if company is None:
        logger.warning("Rejected request to %s: unknown API key.", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )

    return company


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """FastAPI dependency: resolve the authenticated end-user from a Bearer JWT."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token.",
        )

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        logger.warning("Rejected JWT on %s: invalid token.", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from None

    try:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
    except Exception:
        logger.exception("Database error while resolving user_id=%s from JWT.", user_id)
        raise

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return user


async def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency: require an authenticated admin tied to a company."""
    if user.role != "admin":
        logger.warning("Forbidden: user_id=%s role=%s is not admin.", user.id, user.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user
