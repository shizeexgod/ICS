"""YooKassa billing endpoints for ICS Pro/Max subscriptions."""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import get_current_admin_company
from app.models.company import Company
from app.models.company_payment import CompanyPayment
from app.schemas.billing import (
    BillingStatusOut,
    CreatePaymentRequest,
    CreatePaymentResponse,
    ReferralProgramOut,
    ValidateReferralRequest,
    ValidateReferralResponse,
    YooKassaWebhookEvent,
)
from app.services.billing_service import (
    create_plan_payment,
    process_successful_payment,
    yookassa_configured,
)
from app.services.plan_service import can_send_reminders, company_plan_out
from app.services.referral_service import (
    REFERRAL_DISCOUNT_PERCENT,
    REFERRAL_REWARD_PERCENT,
    apply_referral_to_payment_amount,
    buyer_eligible_for_referral_discount,
    ensure_company_referral_code,
)
from app.schemas.company import PLAN_PRICING

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


def _default_return_url() -> str:
    return settings.YOOKASSA_RETURN_URL or "https://ics.vercel.app/?billing=success"


@router.get("/status", response_model=BillingStatusOut)
async def get_billing_status(
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> BillingStatusOut:
    """Return current plan state and latest payment status."""
    result = await session.execute(
        select(CompanyPayment)
        .where(CompanyPayment.company_id == company.id)
        .order_by(CompanyPayment.created_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    plan = company_plan_out(company)
    is_pro = company.plan in ("pro", "max") and company.subscription_status == "active"
    return BillingStatusOut(
        plan=company.plan,
        subscription_status=company.subscription_status,
        billing_period=plan.billing_period,
        subscription_ends_at=plan.subscription_ends_at,
        pro_price_rub=company.pro_price_rub,
        is_pro=is_pro,
        can_send_reminders=can_send_reminders(company),
        latest_payment_status=latest.status if latest else None,
    )


@router.post("/create-payment", response_model=CreatePaymentResponse)
async def create_payment(
    payload: CreatePaymentRequest,
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> CreatePaymentResponse:
    """Create a YooKassa redirect payment for a Pro/Max subscription."""
    now = dt.datetime.now(dt.timezone.utc)
    ends_at = company.subscription_ends_at
    if ends_at is not None and ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=dt.timezone.utc)
    has_future_subscription = ends_at is not None and ends_at > now
    if (
        company.plan == payload.plan
        and company.subscription_status == "active"
        and has_future_subscription
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Company already has an active {payload.plan.capitalize()} subscription.",
        )

    if not yookassa_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment provider is not configured. Contact support.",
        )

    return_url = str(payload.return_url or _default_return_url())

    try:
        payment_id, confirmation_url, amount_rub = await create_plan_payment(
            session,
            company=company,
            plan=payload.plan,
            billing_period=payload.billing_period,
            return_url=return_url,
            referral_code=payload.referral_code,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create YooKassa payment for company_id=%s", company.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create payment. Please try again later.",
        ) from None

    return CreatePaymentResponse(
        payment_id=payment_id,
        confirmation_url=confirmation_url,
        amount_rub=amount_rub,
    )


@router.post("/validate-referral", response_model=ValidateReferralResponse)
async def validate_referral_code(
    payload: ValidateReferralRequest,
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> ValidateReferralResponse:
    """Preview referral discount for the company's first paid subscription."""
    original_amount_rub = PLAN_PRICING[payload.plan][payload.billing_period]
    amount_rub, discount_rub, _ = await apply_referral_to_payment_amount(
        session,
        buyer=company,
        original_amount_rub=original_amount_rub,
        referral_code=payload.referral_code,
    )
    return ValidateReferralResponse(
        discount_percent=REFERRAL_DISCOUNT_PERCENT,
        discount_rub=discount_rub,
        final_amount_rub=amount_rub,
        original_amount_rub=original_amount_rub,
    )


@router.get("/referral", response_model=ReferralProgramOut)
async def get_referral_program(
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> ReferralProgramOut:
    """Return referral code, balance and program terms for the dashboard."""
    code = await ensure_company_referral_code(session, company)
    referrals_result = await session.execute(
        select(func.count())
        .select_from(Company)
        .where(Company.referred_by_company_id == company.id)
    )
    referrals_count = int(referrals_result.scalar() or 0)
    await session.commit()

    discount_available = await buyer_eligible_for_referral_discount(session, company)
    return ReferralProgramOut(
        code=code,
        balance_rub=company.referral_balance_rub,
        reward_percent=REFERRAL_REWARD_PERCENT,
        discount_percent=REFERRAL_DISCOUNT_PERCENT,
        referrals_count=referrals_count,
        discount_available=discount_available,
    )


@router.post("/webhook")
async def yookassa_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Handle YooKassa payment notifications (payment.succeeded)."""
    try:
        body = await request.json()
        event = YooKassaWebhookEvent.model_validate(body)
    except Exception:
        logger.exception("Invalid YooKassa webhook payload.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload.") from None

    if event.event != "payment.succeeded":
        return {"status": "ignored"}

    payment_id = event.object.get("id")
    if not payment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing payment id.")

    metadata = event.object.get("metadata") or {}
    company_id = None
    if metadata.get("company_id"):
        try:
            company_id = uuid.UUID(metadata["company_id"])
        except ValueError:
            logger.warning("Invalid company_id in webhook metadata: %s", metadata.get("company_id"))

    try:
        await process_successful_payment(session, payment_id=payment_id, company_id=company_id)
    except Exception:
        logger.exception("Failed to process YooKassa webhook for payment_id=%s", payment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process payment.",
        ) from None

    return {"status": "ok"}
