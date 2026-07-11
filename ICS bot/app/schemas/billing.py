"""Pydantic schemas for YooKassa billing."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class CreatePaymentRequest(BaseModel):
    plan: Literal["pro", "max"]
    billing_period: Literal["monthly", "annual"]
    return_url: HttpUrl | str | None = None


class CreatePaymentResponse(BaseModel):
    ok: bool = True
    payment_id: str
    confirmation_url: str
    amount_rub: int


class BillingStatusOut(BaseModel):
    plan: str
    subscription_status: str
    billing_period: str | None = None
    subscription_ends_at: datetime | None = None
    pro_price_rub: int
    is_pro: bool
    can_send_reminders: bool
    latest_payment_status: str | None = None


class YooKassaWebhookEvent(BaseModel):
    event: str
    object: dict
