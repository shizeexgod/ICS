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
    referral_code: str | None = Field(default=None, max_length=16)

    @field_validator("referral_code")
    @classmethod
    def _strip_referral_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        return value or None


class ValidateReferralRequest(BaseModel):
    referral_code: str = Field(..., min_length=4, max_length=16)
    plan: Literal["pro", "max"] = "pro"
    billing_period: Literal["monthly", "annual"] = "monthly"

    @field_validator("referral_code")
    @classmethod
    def _strip_referral_code(cls, value: str) -> str:
        return value.strip().upper()


class ValidateReferralResponse(BaseModel):
    ok: bool = True
    discount_percent: int
    discount_rub: int
    final_amount_rub: int
    original_amount_rub: int


class ReferralProgramOut(BaseModel):
    code: str
    balance_rub: int
    reward_percent: int
    discount_percent: int
    referrals_count: int
    discount_available: bool


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
