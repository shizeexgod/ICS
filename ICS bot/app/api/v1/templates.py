"""Admin-only Telegram notification template management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import supabase
from app.core.security import get_current_admin
from app.models.user import User
from app.schemas.templates import (
    TemplateListResponse,
    TemplateOut,
    TemplateSaveRequest,
    TemplateSaveResponse,
    TemplateUpdateRequest,
)
from app.services.template_service import TEMPLATE_CATALOG, list_company_templates, seed_default_templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    admin: User = Depends(get_current_admin),
) -> TemplateListResponse:
    """List all notification templates for the admin's company."""
    if admin.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin account is not linked to a company.",
        )

    items = await list_company_templates(admin.company_id)
    if not any(item.get("is_customized") for item in items):
        await seed_default_templates(admin.company_id)
        items = await list_company_templates(admin.company_id)
    return TemplateListResponse(templates=[TemplateOut(**item) for item in items])


@router.patch("/{event_type}", response_model=TemplateSaveResponse)
async def update_template(
    event_type: str,
    payload: TemplateUpdateRequest,
    admin: User = Depends(get_current_admin),
) -> TemplateSaveResponse:
    """Update template text and/or enabled flag."""
    if admin.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin account is not linked to a company.",
        )

    event_type = event_type.strip()
    if event_type not in TEMPLATE_CATALOG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown template event type.",
        )

    if payload.tg_template is None and payload.is_enabled is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nothing to update.",
        )

    company_id = str(admin.company_id)
    meta = TEMPLATE_CATALOG[event_type]
    existing = await (
        supabase.table("notification_templates")
        .select("tg_template", "is_enabled")
        .eq("company_id", company_id)
        .eq("event_type", event_type)
        .execute_async()
    )
    rows = existing.data or []
    current_template = rows[0]["tg_template"] if rows else meta["default"]
    current_enabled = bool(rows[0]["is_enabled"]) if rows else True

    update_row = {
        "company_id": company_id,
        "event_type": event_type,
        "tg_template": payload.tg_template.strip() if payload.tg_template is not None else current_template,
        "is_enabled": payload.is_enabled if payload.is_enabled is not None else current_enabled,
    }

    try:
        result = await (
            supabase.table("notification_templates")
            .upsert(update_row, on_conflict="company_id,event_type")
            .execute_async()
        )
        saved_rows = result.data or []
        if not saved_rows:
            refetch = await (
                supabase.table("notification_templates")
                .select("event_type", "is_enabled")
                .eq("company_id", company_id)
                .eq("event_type", event_type)
                .execute_async()
            )
            saved_rows = refetch.data or []
    except Exception:
        logger.exception(
            "Failed to update template company_id=%s event_type=%s",
            company_id,
            event_type,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template.",
        ) from None

    saved = saved_rows[0] if saved_rows else update_row
    return TemplateSaveResponse(
        event_type=event_type,
        is_enabled=bool(saved.get("is_enabled", update_row["is_enabled"])),
        message="Template updated.",
    )


@router.post("/save", response_model=TemplateSaveResponse)
async def save_template(
    payload: TemplateSaveRequest,
    admin: User = Depends(get_current_admin),
) -> TemplateSaveResponse:
    """Upsert a Telegram notification template for the admin's company."""
    if admin.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin account is not linked to a company.",
        )

    event_type = payload.event_type.strip()
    if event_type not in TEMPLATE_CATALOG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown template event type.",
        )

    tg_template = payload.tg_template.strip()
    company_id = str(admin.company_id)
    is_enabled = True if payload.is_enabled is None else payload.is_enabled

    try:
        result = await (
            supabase.table("notification_templates")
            .upsert(
                {
                    "company_id": company_id,
                    "event_type": event_type,
                    "tg_template": tg_template,
                    "is_enabled": is_enabled,
                },
                on_conflict="company_id,event_type",
            )
            .execute_async()
        )
        rows = result.data or []
        if not rows:
            refetch = await (
                supabase.table("notification_templates")
                .select("event_type", "is_enabled")
                .eq("company_id", company_id)
                .eq("event_type", event_type)
                .execute_async()
            )
            rows = refetch.data or []
    except Exception:
        logger.exception(
            "Failed to save template company_id=%s event_type=%s",
            company_id,
            event_type,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save template.",
        ) from None

    saved = rows[0] if rows else {}
    return TemplateSaveResponse(
        event_type=event_type,
        is_enabled=bool(saved.get("is_enabled", is_enabled)),
    )
