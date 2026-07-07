"""Typed callback_data factories for inline keyboard buttons (aiogram v3 style)."""

from __future__ import annotations

import uuid

from aiogram.filters.callback_data import CallbackData


class ConfirmBookingCallback(CallbackData, prefix="confirm_booking"):
    """Inline button payload: ``confirm_booking:<appointment_id>``."""

    appointment_id: uuid.UUID
