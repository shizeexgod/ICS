"""Admin-only Telegram notification template management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import supabase
from app.core.security import get_current_admin
from app.models.user import User
from app.schemas.templates import TemplateSaveRequest, TemplateSaveResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


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
    tg_template = payload.tg_template.strip()
    company_id = str(admin.company_id)

    try:
        result = await (
            supabase.table("notification_templates")
            .upsert(
                {
                    "company_id": company_id,
                    "event_type": event_type,
                    "tg_template": tg_template,
                    "is_enabled": True,
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
        is_enabled=bool(saved.get("is_enabled", True)),
    )
