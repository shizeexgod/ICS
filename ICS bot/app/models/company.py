"""ORM model for the `companies` table."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.client import Client
    from app.models.company_manager import CompanyManager
    from app.models.company_staff import CompanyStaff


class Company(Base):
    """A tenant business using the booking system (identified by its API key).

    NOTE: this must mirror the real Supabase schema exactly. The actual table has
    `id`/`company_id`/`client_id` columns of type `uuid` (generated app-side, no
    DB-level default), a required `owner_email` column, and no `updated_at` column.
    """

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="trial", index=True)
    trial_ends_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscription_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    billing_period: Mapped[str] = mapped_column(String(10), nullable=False, default="monthly")
    subscription_ends_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reminders_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reminders_period_start: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pro_price_rub: Mapped[int] = mapped_column(Integer, nullable=False, default=5000)
    referral_code: Mapped[str | None] = mapped_column(String(16), nullable=True, unique=True)
    referred_by_company_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    referral_balance_rub: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    referral_discount_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    clients: Mapped[list["Client"]] = relationship(
        "Client", back_populates="company", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="company", cascade="all, delete-orphan"
    )
    managers: Mapped[list["CompanyManager"]] = relationship(
        "CompanyManager", back_populates="company", cascade="all, delete-orphan"
    )
    staff: Mapped[list["CompanyStaff"]] = relationship(
        "CompanyStaff", back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Company(id={self.id!r}, name={self.name!r})"
