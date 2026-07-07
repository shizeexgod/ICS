"""ORM model for the `appointments` table."""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.company import Company


class AppointmentStatus(str, enum.Enum):
    """Lifecycle status of a booked appointment."""

    SCHEDULED = "scheduled"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Appointment(Base):
    """A single booked service slot for a client, scoped to a company (tenant).

    NOTE: mirrors the real Supabase schema. `status` is a plain `varchar` column
    (no native Postgres enum type exists), so `native_enum=False` is required or
    SQLAlchemy will try to bind/create a Postgres ENUM type that doesn't exist.
    `price` is `NOT NULL` with no DB-side default. There is no `created_at`
    column on this table (only `updated_at`), unlike `clients`/`companies`.
    """

    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    appointment_date: Mapped[dt.date] = mapped_column(nullable=False)
    appointment_time: Mapped[dt.time] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    status: Mapped[AppointmentStatus] = mapped_column(
        SAEnum(
            AppointmentStatus,
            name="appointment_status",
            native_enum=False,
            length=32,
            validate_strings=True,
        ),
        default=AppointmentStatus.SCHEDULED,
        nullable=False,
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    company: Mapped["Company"] = relationship("Company", back_populates="appointments")
    client: Mapped["Client"] = relationship("Client", back_populates="appointments")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"Appointment(id={self.id!r}, company_id={self.company_id!r}, "
            f"client_id={self.client_id!r}, service_name={self.service_name!r}, "
            f"date={self.appointment_date!r}, time={self.appointment_time!r}, "
            f"status={self.status!r})"
        )
