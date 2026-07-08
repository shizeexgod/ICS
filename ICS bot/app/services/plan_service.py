"""Subscription plan helpers for trial / pro gating."""

from __future__ import annotations

import datetime as dt

from app.models.company import Company
from app.schemas.company import (
    PRO_PRICE_RUB,
    TRIAL_DAYS,
    TRIAL_REMINDER_LIMIT,
    CompanyPlanOut,
)


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def is_trial_active(company: Company, *, now: dt.datetime | None = None) -> bool:
    now = now or _utc_now()
    if company.plan == "pro" and company.subscription_status == "active":
        return False
    if company.trial_ends_at is None:
        return company.plan == "trial"
    ends_at = company.trial_ends_at
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=dt.timezone.utc)
    return company.plan == "trial" and ends_at >= now


def can_send_reminders(company: Company, *, now: dt.datetime | None = None) -> bool:
    now = now or _utc_now()
    if company.plan == "pro" and company.subscription_status == "active":
        return True
    if not is_trial_active(company, now=now):
        return False
    return company.reminders_used < TRIAL_REMINDER_LIMIT


def trial_days_left(company: Company, *, now: dt.datetime | None = None) -> int | None:
    if company.plan != "trial" or company.trial_ends_at is None:
        return None
    now = now or _utc_now()
    ends_at = company.trial_ends_at
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=dt.timezone.utc)
    delta = ends_at - now
    return max(0, delta.days)


def company_plan_out(company: Company, *, now: dt.datetime | None = None) -> CompanyPlanOut:
    now = now or _utc_now()
    trial_active = is_trial_active(company, now=now)
    is_pro = company.plan == "pro" and company.subscription_status == "active"
    reminders_limit = None if is_pro else TRIAL_REMINDER_LIMIT
    remaining = None
    if trial_active:
        remaining = max(0, TRIAL_REMINDER_LIMIT - company.reminders_used)
    return CompanyPlanOut(
        plan=company.plan,
        trial_ends_at=company.trial_ends_at,
        subscription_status=company.subscription_status,
        reminders_used=company.reminders_used,
        reminders_limit=reminders_limit,
        reminders_remaining=remaining,
        trial_days_left=trial_days_left(company, now=now),
        pro_price_rub=company.pro_price_rub or PRO_PRICE_RUB,
        is_trial_active=trial_active,
        can_send_reminders=can_send_reminders(company, now=now),
    )


def init_trial_fields(company: Company, *, now: dt.datetime | None = None) -> None:
    now = now or _utc_now()
    company.plan = "trial"
    company.trial_ends_at = now + dt.timedelta(days=TRIAL_DAYS)
    company.subscription_status = "active"
    company.reminders_used = 0
    company.reminders_period_start = now
    company.pro_price_rub = PRO_PRICE_RUB
