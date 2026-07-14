"""Referral codes: first-purchase discount and referrer rewards."""

from __future__ import annotations

import secrets
import string
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.company_payment import CompanyPayment

REFERRAL_REWARD_PERCENT = 20
REFERRAL_DISCOUNT_PERCENT = 10

_CODE_ALPHABET = string.ascii_uppercase + string.digits


def normalize_referral_code(code: str | None) -> str | None:
    if not code:
        return None
    value = code.strip().upper().replace(" ", "")
    return value or None


def generate_referral_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


async def ensure_company_referral_code(session: AsyncSession, company: Company) -> str:
    """Return the company's referral code, generating one if missing."""
    if company.referral_code:
        return company.referral_code

    for _ in range(12):
        candidate = generate_referral_code()
        exists = await session.execute(
            select(Company.id).where(Company.referral_code == candidate)
        )
        if exists.scalar_one_or_none() is None:
            company.referral_code = candidate
            await session.flush()
            return candidate

    raise RuntimeError("Failed to generate a unique referral code.")


async def count_successful_payments(session: AsyncSession, company_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(CompanyPayment)
        .where(
            CompanyPayment.company_id == company_id,
            CompanyPayment.status == "succeeded",
        )
    )
    return int(result.scalar() or 0)


async def buyer_eligible_for_referral_discount(session: AsyncSession, company: Company) -> bool:
    if company.referral_discount_used:
        return False
    return await count_successful_payments(session, company.id) == 0


async def resolve_referrer(
    session: AsyncSession,
    *,
    buyer: Company,
    code: str,
) -> Company:
    normalized = normalize_referral_code(code)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid referral code.",
        )

    result = await session.execute(
        select(Company).where(Company.referral_code == normalized)
    )
    referrer = result.scalar_one_or_none()
    if referrer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral code not found.",
        )
    if referrer.id == buyer.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot use your own referral code.",
        )
    return referrer


def calculate_referral_discount(original_amount_rub: int) -> int:
    return int(original_amount_rub * REFERRAL_DISCOUNT_PERCENT / 100)


def calculate_referral_reward(gross_amount_rub: int) -> int:
    return int(gross_amount_rub * REFERRAL_REWARD_PERCENT / 100)


async def apply_referral_to_payment_amount(
    session: AsyncSession,
    *,
    buyer: Company,
    original_amount_rub: int,
    referral_code: str | None,
) -> tuple[int, int, uuid.UUID | None]:
    """Return (amount_to_charge, discount_rub, referrer_company_id)."""
    if not referral_code:
        return original_amount_rub, 0, None

    if not await buyer_eligible_for_referral_discount(session, buyer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Referral discount is only available on the first paid subscription.",
        )

    referrer = await resolve_referrer(session, buyer=buyer, code=referral_code)
    discount_rub = calculate_referral_discount(original_amount_rub)
    amount_rub = max(original_amount_rub - discount_rub, 1)
    return amount_rub, discount_rub, referrer.id


async def process_referral_reward(
    session: AsyncSession,
    payment_row: CompanyPayment,
) -> None:
    """Credit referrer after a successful referred payment (idempotent)."""
    if (
        payment_row.referrer_company_id is None
        or payment_row.referral_reward_applied
        or payment_row.status != "succeeded"
    ):
        return

    gross = payment_row.original_amount_rub or payment_row.amount_rub
    reward_rub = calculate_referral_reward(gross)

    referrer_result = await session.execute(
        select(Company).where(Company.id == payment_row.referrer_company_id)
    )
    referrer = referrer_result.scalar_one_or_none()
    if referrer is None:
        return

    buyer_result = await session.execute(
        select(Company).where(Company.id == payment_row.company_id)
    )
    buyer = buyer_result.scalar_one_or_none()

    referrer.referral_balance_rub += reward_rub
    payment_row.referral_reward_applied = True

    if buyer is not None:
        buyer.referral_discount_used = True
        if buyer.referred_by_company_id is None:
            buyer.referred_by_company_id = referrer.id
