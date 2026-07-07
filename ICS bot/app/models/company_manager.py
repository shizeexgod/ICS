"""ORM model for the `company_managers` table.

Maps a Telegram chat id to the company it administers, so the webhook layer
can fan out booking notifications to every admin of a given tenant instead of
relying on a single hardcoded chat id from `.env`.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.company import Company


class CompanyManager(Base):
    """A Telegram chat (admin/manager) subscribed to a company's booking notifications.

    `tg_chat_id` is `BigInteger` because Telegram chat/user ids routinely exceed
    the 32-bit `int4` range. There is no DB-level unique constraint enforced by
    this model beyond the primary key; duplicate `(company_id, tg_chat_id)` pairs
    are prevented in application code (see `_bind_manager` in `app/bot/handlers.py`).
    """

    __tablename__ = "company_managers"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tg_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    company: Mapped["Company"] = relationship("Company", back_populates="managers")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"CompanyManager(id={self.id!r}, company_id={self.company_id!r}, "
            f"tg_chat_id={self.tg_chat_id!r})"
        )
