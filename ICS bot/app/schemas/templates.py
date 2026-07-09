"""Pydantic schemas for Telegram notification template management."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TemplateSaveRequest(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    tg_template: str = Field(..., min_length=1)
    is_enabled: bool | None = None


class TemplateUpdateRequest(BaseModel):
    tg_template: str | None = Field(default=None, min_length=1)
    is_enabled: bool | None = None


class TemplateOut(BaseModel):
    event_type: str
    title: str
    description: str
    channel: str
    placeholders: list[str]
    tg_template: str
    is_enabled: bool
    is_customized: bool = False


class TemplateListResponse(BaseModel):
    templates: list[TemplateOut]


class TemplateSaveResponse(BaseModel):
    ok: bool = True
    message: str = "Template saved."
    event_type: str
    is_enabled: bool = True
