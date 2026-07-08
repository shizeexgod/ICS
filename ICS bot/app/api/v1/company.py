"""Company onboarding and tenant profile endpoints."""

from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models.company import Company
from app.models.user import User
from app.schemas.auth import UserOut
from app.schemas.company import CompanyOut, CompanySetupRequest, CompanySetupResponse
from app.services.auth_service import create_access_token, create_refresh_token, normalize_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/company", tags=["company"])


def _generate_api_key() -> str:
    return secrets.token_hex(32)


def _company_out(company: Company) -> CompanyOut:
    return CompanyOut(
        id=company.id,
        name=company.name,
        owner_email=company.owner_email,
        api_key=company.api_key,
        created_at=company.created_at,
    )


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        phone=user.phone,
        tg_chat_id=user.tg_chat_id,
        company_id=user.company_id,
        role=user.role,
        created_at=user.created_at,
    )


@router.post("/setup", response_model=CompanySetupResponse)
async def setup_company(
    payload: CompanySetupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CompanySetupResponse:
    """Create a tenant company for a new user and promote them to admin."""
    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    if user.company_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company is already configured for this account.",
        )

    owner_email = normalize_email(str(payload.owner_email or user.email))
    api_key = _generate_api_key()
    company = Company(
        name=payload.company_name,
        owner_email=owner_email,
        api_key=api_key,
    )
    session.add(company)

    try:
        await session.flush()
        user.company_id = company.id
        user.role = "admin"
        await session.commit()
        await session.refresh(company)
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        logger.exception(
            "Failed to create company for user_id=%s name=%r",
            user.id,
            payload.company_name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create company. Please try again.",
        ) from None

    access_token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    refresh_token = create_refresh_token(user_id=user.id, email=user.email)

    logger.info(
        "Company onboarded company_id=%s user_id=%s email=%s",
        company.id,
        user.id,
        user.email,
    )
    return CompanySetupResponse(
        company=_company_out(company),
        user=_user_out(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=CompanyOut)
async def get_my_company(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyOut:
    """Return the authenticated user's company profile."""
    if current_user.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company is not configured yet.",
        )

    result = await session.execute(
        select(Company).where(Company.id == current_user.company_id)
    )
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found.",
        )

    return _company_out(company)
