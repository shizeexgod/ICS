"""APScheduler-based appointment reminders.

Schedules a one-off reminder job exactly `_REMINDER_LEAD_TIME` before each
appointment. The job re-checks the appointment's current status in Supabase
right before firing (so a cancellation after booking is respected) and then
notifies the client over WhatsApp + SMS.

NOTE: this uses APScheduler's default in-memory job store, so scheduled
reminders are lost if the process restarts. For a production deployment,
switch to a persistent job store (e.g. `SQLAlchemyJobStore`) so pending
reminders survive a redeploy/crash — out of scope for now, but flagged here
so it isn't forgotten.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.services.notifications import notify_client

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler = AsyncIOScheduler()

_REMINDER_LEAD_TIME = dt.timedelta(hours=2)


def start_scheduler() -> None:
    """Start the scheduler. Intended to be called once from FastAPI's lifespan."""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started.")


def shutdown_scheduler() -> None:
    """Stop the scheduler gracefully. Intended to be called from FastAPI's lifespan."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")


def schedule_appointment_reminder(
    appointment_id: uuid.UUID, appointment_datetime: dt.datetime
) -> None:
    """Schedule a one-off reminder job to run `_REMINDER_LEAD_TIME` before the visit.

    If the computed reminder time has already passed (e.g. the booking was made
    less than 2 hours before the appointment), no job is scheduled — logged and
    skipped, rather than firing an immediate/late reminder.
    """
    run_date = appointment_datetime - _REMINDER_LEAD_TIME
    now = dt.datetime.now()

    if run_date <= now:
        logger.info(
            "Skipping reminder for appointment_id=%s: computed run_date=%s is already in the past "
            "(appointment_datetime=%s).",
            appointment_id,
            run_date,
            appointment_datetime,
        )
        return

    job_id = f"appointment-reminder-{appointment_id}"
    scheduler.add_job(
        _send_appointment_reminder,
        trigger="date",
        run_date=run_date,
        args=[appointment_id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=60 * 30,
    )
    logger.info(
        "Scheduled reminder job %s for appointment_id=%s at run_date=%s",
        job_id,
        appointment_id,
        run_date,
    )


async def _send_appointment_reminder(appointment_id: uuid.UUID) -> None:
    """Job body: re-check the appointment is still active, then notify the client."""
    logger.info("Running reminder job for appointment_id=%s", appointment_id)

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Appointment)
                .options(selectinload(Appointment.client))
                .where(Appointment.id == appointment_id)
            )
            appointment = result.scalars().first()

            if appointment is None:
                logger.warning(
                    "Reminder skipped: appointment_id=%s no longer exists.", appointment_id
                )
                return

            if appointment.status in (
                AppointmentStatus.CANCELLED,
                AppointmentStatus.COMPLETED,
            ):
                logger.info(
                    "Reminder skipped: appointment_id=%s has status=%s.",
                    appointment_id,
                    appointment.status.value,
                )
                return

            if appointment.status not in (
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.SCHEDULED,
            ):
                logger.info(
                    "Reminder skipped: appointment_id=%s has unexpected status=%s.",
                    appointment_id,
                    appointment.status.value,
                )
                return

            client_phone = appointment.client.phone
            service_name = appointment.service_name
            appointment_time = appointment.appointment_time
    except Exception:  # noqa: BLE001 - a broken reminder job must never crash the scheduler
        logger.exception("Failed to load appointment_id=%s for its reminder job.", appointment_id)
        return

    reminder_text = (
        f"Напоминаем, вы записаны сегодня в {appointment_time.isoformat(timespec='minutes')} "
        f"на услугу {service_name}!"
    )

    try:
        await notify_client(client_phone, reminder_text)
    except Exception:  # noqa: BLE001 - a broken reminder job must never crash the scheduler
        logger.exception(
            "Failed to send reminder notifications for appointment_id=%s", appointment_id
        )
