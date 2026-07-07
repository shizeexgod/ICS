"""ORM model for the `clients` table."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.company import Company


class Client(Base):
    """A person known to a specific company, identified by phone number and/or Telegram id.

    NOTE: mirrors the real Supabase schema. There is no DB-level unique constraint
    on `(company_id, phone)` — that scoping is enforced entirely in application
    code (see `_get_or_create_client` in `app/api/webhooks.py`). `preferred_messenger`
    is `NOT NULL` with no DB-side default, so a Python-side default is required here.
    """

    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tg_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    preferred_messenger: Mapped[str] = mapped_column(
        String(32), nullable=False, default="telegram"
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship("Company", back_populates="clients")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"Client(id={self.id!r}, company_id={self.company_id!r}, "
            f"full_name={self.full_name!r}, phone={self.phone!r})"
        )
