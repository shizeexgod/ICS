"""YooKassa payment creation and Pro/Max plan activation."""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Literal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.company import Company
from app.models.company_payment import CompanyPayment
from app.schemas.company import PLAN_PRICING
from app.services.plan_service import activate_paid_plan
from app.services.referral_service import (
    apply_referral_to_payment_amount,
    process_referral_reward,
)

logger = logging.getLogger(__name__)

_YOOKASSA_API = "https://api.yookassa.ru/v3/payments"

_PERIOD_LABEL = {"monthly": "30 дней", "semiannual": "6 месяцев", "annual": "1 год"}


def yookassa_configured() -> bool:
    return bool(settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY)


async def create_plan_payment(
    session: AsyncSession,
    *,
    company: Company,
    plan: Literal["pro", "max"],
    billing_period: Literal["monthly", "semiannual", "annual"],
    return_url: str,
    referral_code: str | None = None,
) -> tuple[str, str, int]:
    """Create a YooKassa redirect payment and persist a pending row."""
    if not yookassa_configured():
        raise RuntimeError("YooKassa is not configured on the server.")

    original_amount_rub = PLAN_PRICING[plan][billing_period]
    amount_rub, discount_rub, referrer_company_id = await apply_referral_to_payment_amount(
        session,
        buyer=company,
        original_amount_rub=original_amount_rub,
        referral_code=referral_code,
    )
    idempotence_key = str(uuid.uuid4())
    metadata = {"company_id": str(company.id)}
    if referrer_company_id is not None:
        metadata["referrer_company_id"] = str(referrer_company_id)
    payload = {
        "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": f"ICS {plan.capitalize()} ({_PERIOD_LABEL[billing_period]}) — {company.name}",
        "metadata": metadata,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            _YOOKASSA_API,
            json=payload,
            auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
            headers={
                "Idempotence-Key": idempotence_key,
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()

    payment_id = data["id"]
    confirmation_url = data["confirmation"]["confirmation_url"]

    payment_row = CompanyPayment(
        company_id=company.id,
        yookassa_payment_id=payment_id,
        amount_rub=amount_rub,
        original_amount_rub=original_amount_rub,
        discount_rub=discount_rub,
        referrer_company_id=referrer_company_id,
        plan=plan,
        billing_period=billing_period,
        status=data.get("status", "pending"),
    )
    session.add(payment_row)
    await session.commit()

    return payment_id, confirmation_url, amount_rub


async def fetch_yookassa_payment(payment_id: str) -> dict:
    """Fetch payment state from YooKassa API."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            f"{_YOOKASSA_API}/{payment_id}",
            auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
        )
        response.raise_for_status()
        return response.json()


async def process_successful_payment(
    session: AsyncSession,
    *,
    payment_id: str,
    company_id: uuid.UUID | None = None,
) -> bool:
    """Verify payment with YooKassa and upgrade company to Pro/Max (idempotent)."""
    if not yookassa_configured():
        logger.warning("YooKassa not configured; cannot process payment_id=%s", payment_id)
        return False

    data = await fetch_yookassa_payment(payment_id)
    if data.get("status") != "succeeded":
        logger.info("Payment %s status=%s; skipping activation.", payment_id, data.get("status"))
        return False

    metadata = data.get("metadata") or {}
    resolved_company_id = company_id or uuid.UUID(metadata["company_id"])

    result = await session.execute(
        select(CompanyPayment).where(CompanyPayment.yookassa_payment_id == payment_id)
    )
    payment_row = result.scalar_one_or_none()
    if payment_row is not None and payment_row.status == "succeeded":
        return True

    now = dt.datetime.now(dt.timezone.utc)
    # The webhook only carries the YooKassa payment id, not the plan/period the
    # merchant selected — read those back off the row we stored when the
    # payment was created. Fall back to pro/monthly only if that row is
    # somehow missing (should not happen in normal flow).
    plan: Literal["pro", "max"] = payment_row.plan if payment_row is not None else "pro"  # type: ignore[assignment]
    billing_period: Literal["monthly", "semiannual", "annual"] = (
        payment_row.billing_period if payment_row is not None else "monthly"  # type: ignore[assignment]
    )

    if payment_row is None:
        payment_row = CompanyPayment(
            company_id=resolved_company_id,
            yookassa_payment_id=payment_id,
            amount_rub=int(float(data["amount"]["value"])),
            original_amount_rub=int(float(data["amount"]["value"])),
            plan=plan,
            billing_period=billing_period,
            status="succeeded",
            paid_at=now,
        )
        session.add(payment_row)
    else:
        payment_row.status = "succeeded"
        payment_row.paid_at = now
        if payment_row.original_amount_rub is None:
            payment_row.original_amount_rub = payment_row.amount_rub

    await activate_paid_plan(session, resolved_company_id, plan, billing_period)
    await process_referral_reward(session, payment_row)
    await session.commit()
    logger.info(
        "Activated %s (%s) for company_id=%s via payment_id=%s",
        plan,
        billing_period,
        resolved_company_id,
        payment_id,
    )
    return True
