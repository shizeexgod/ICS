"""YooKassa billing endpoints for ICS Pro subscriptions."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
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
    YooKassaWebhookEvent,
)
from app.services.billing_service import (
    create_pro_payment,
    process_successful_payment,
    yookassa_configured,
)
from app.services.plan_service import can_send_reminders, company_plan_out

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
    is_pro = company.plan == "pro" and company.subscription_status == "active"
    return BillingStatusOut(
        plan=company.plan,
        subscription_status=company.subscription_status,
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
    """Create a YooKassa redirect payment for Pro subscription."""
    if company.plan == "pro" and company.subscription_status == "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company already has an active Pro subscription.",
        )

    if not yookassa_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment provider is not configured. Contact support.",
        )

    return_url = str(payload.return_url or _default_return_url())

    try:
        payment_id, confirmation_url, amount_rub = await create_pro_payment(
            session,
            company=company,
            return_url=return_url,
        )
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
