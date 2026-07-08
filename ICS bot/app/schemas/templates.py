"""Pydantic schemas for Telegram notification template management."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TemplateSaveRequest(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    tg_template: str = Field(..., min_length=1)


class TemplateSaveResponse(BaseModel):
    ok: bool = True
    message: str = "Template saved."
    event_type: str
    is_enabled: bool = True
