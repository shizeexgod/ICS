"""ORM model for the `company_payments` table."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CompanyPayment(Base):
    __tablename__ = "company_payments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    yookassa_payment_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    amount_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    original_amount_rub: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_rub: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    referrer_company_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    referral_reward_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plan: Mapped[str] = mapped_column(String(10), nullable=False, default="pro")
    billing_period: Mapped[str] = mapped_column(String(10), nullable=False, default="monthly")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    paid_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
