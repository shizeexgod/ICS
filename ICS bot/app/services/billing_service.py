"""YooKassa payment creation and Pro plan activation."""

from __future__ import annotations

import datetime as dt
import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.company import Company
from app.models.company_payment import CompanyPayment
from app.services.plan_service import activate_pro_plan

logger = logging.getLogger(__name__)

_YOOKASSA_API = "https://api.yookassa.ru/v3/payments"


def yookassa_configured() -> bool:
    return bool(settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY)


async def create_pro_payment(
    session: AsyncSession,
    *,
    company: Company,
    return_url: str,
) -> tuple[str, str, int]:
    """Create a YooKassa redirect payment and persist a pending row."""
    if not yookassa_configured():
        raise RuntimeError("YooKassa is not configured on the server.")

    amount_rub = company.pro_price_rub or 5000
    idempotence_key = str(uuid.uuid4())
    payload = {
        "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": f"ICS Pro — {company.name}",
        "metadata": {"company_id": str(company.id)},
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
    """Verify payment with YooKassa and upgrade company to Pro (idempotent)."""
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
    if payment_row is None:
        payment_row = CompanyPayment(
            company_id=resolved_company_id,
            yookassa_payment_id=payment_id,
            amount_rub=int(float(data["amount"]["value"])),
            status="succeeded",
            paid_at=now,
        )
        session.add(payment_row)
    else:
        payment_row.status = "succeeded"
        payment_row.paid_at = now

    await activate_pro_plan(session, resolved_company_id)
    await session.commit()
    logger.info("Activated Pro for company_id=%s via payment_id=%s", resolved_company_id, payment_id)
    return True
