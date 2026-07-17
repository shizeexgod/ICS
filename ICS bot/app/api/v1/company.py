"""Company onboarding, profile, stats, appointments (admin JWT)."""

from __future__ import annotations

import datetime as dt
import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_admin, get_current_admin_company, get_current_user
from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.models.company import Company
from app.models.company_manager import CompanyManager
from app.models.company_staff import CompanyStaff
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreateRequest,
    AppointmentCreateResponse,
    AppointmentListItem,
    AppointmentStatusUpdateRequest,
)
from app.schemas.auth import UserOut
from app.schemas.company import (
    CompanyOut,
    CompanySetupRequest,
    CompanySetupResponse,
    CompanyStatsOut,
    CompanyTelegramOut,
    CompanyUpdateRequest,
    StaffCreateRequest,
    StaffOut,
    StaffUpdateRequest,
    TelegramManagerOut,
    UserProfileUpdateRequest,
)
from app.services.auth_service import create_access_token, create_refresh_token, normalize_email
from app.services.booking_service import create_company_appointment
from app.services.notifications import notify_client
from app.services.plan_service import company_plan_out, init_trial_fields
from app.services.referral_service import ensure_company_referral_code
from app.services.staff_service import (
    company_has_active_staff,
    count_active_staff,
    staff_limit_for_plan,
    staff_out,
)
from app.services.template_service import (
    build_appointment_context,
    get_template_text,
    seed_default_templates,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/company", tags=["company"])

_INACTIVE = (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED)


def _generate_api_key() -> str:
    return secrets.token_hex(32)


def _company_out(company: Company) -> CompanyOut:
    return CompanyOut(
        id=company.id,
        name=company.name,
        owner_email=company.owner_email,
        api_key=company.api_key,
        created_at=company.created_at,
        plan=company_plan_out(company),
    )


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        phone=user.phone,
        tg_chat_id=user.tg_chat_id,
        company_id=user.company_id,
        role=user.role,
        created_at=user.created_at,
    )


@router.post("/setup", response_model=CompanySetupResponse)
async def setup_company(
    payload: CompanySetupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CompanySetupResponse:
    """Create a tenant company for a new user and promote them to admin."""
    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    if user.company_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company is already configured for this account.",
        )

    owner_email = normalize_email(str(payload.owner_email or user.email))
    api_key = _generate_api_key()
    company = Company(name=payload.company_name, owner_email=owner_email, api_key=api_key)
    init_trial_fields(company)
    session.add(company)

    try:
        await session.flush()
        await ensure_company_referral_code(session, company)
        user.company_id = company.id
        user.role = "admin"
        await session.commit()
        await session.refresh(company)
        await session.refresh(user)
        await seed_default_templates(company.id)
    except IntegrityError:
        await session.rollback()
        logger.exception("Failed to create company for user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create company. Please try again.",
        ) from None

    access_token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    refresh_token = create_refresh_token(user_id=user.id, email=user.email)

    logger.info("Company onboarded company_id=%s user_id=%s", company.id, user.id)
    return CompanySetupResponse(
        company=_company_out(company),
        user=_user_out(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=CompanyOut)
async def get_my_company(
    company: Company = Depends(get_current_admin_company),
) -> CompanyOut:
    """Return the authenticated admin's company profile."""
    return _company_out(company)


@router.patch("/me", response_model=CompanyOut)
async def update_my_company(
    payload: CompanyUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> CompanyOut:
    """Update company name and owner email."""
    if payload.name is not None:
        company.name = payload.name
    if payload.owner_email is not None:
        company.owner_email = normalize_email(str(payload.owner_email))
    await session.commit()
    await session.refresh(company)
    return _company_out(company)


@router.patch("/profile", response_model=UserOut)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> UserOut:
    """Update admin display name and phone."""
    result = await session.execute(select(User).where(User.id == admin.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip() or None
    await session.commit()
    await session.refresh(user)
    return _user_out(user)


@router.get("/stats", response_model=CompanyStatsOut)
async def get_company_stats(
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> CompanyStatsOut:
    """Dashboard metrics for the admin overview."""
    today = dt.date.today()
    today_result = await session.execute(
        select(func.count(Appointment.id)).where(
            Appointment.company_id == company.id,
            Appointment.appointment_date == today,
            Appointment.status.notin_(_INACTIVE),
        )
    )
    appointments_today = today_result.scalar() or 0

    clients_result = await session.execute(
        select(func.count(func.distinct(Appointment.client_id))).where(
            Appointment.company_id == company.id,
            Appointment.status.notin_(_INACTIVE),
        )
    )
    active_clients = clients_result.scalar() or 0

    reminders_week = company.reminders_used
    try:
        week_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
        reminders_result = await session.execute(
            text(
                """
                SELECT COUNT(*) FROM public.notifications n
                JOIN public.appointments a ON a.id = n.appointment_id
                WHERE a.company_id = :company_id AND n.sent_at >= :week_ago
                """
            ),
            {"company_id": str(company.id), "week_ago": week_ago},
        )
        reminders_week = reminders_result.scalar() or 0
    except Exception:
        logger.debug("notifications table unavailable; using reminders_used fallback")

    return CompanyStatsOut(
        appointments_today=appointments_today,
        active_clients=active_clients,
        reminders_week=reminders_week,
    )


@router.get("/telegram", response_model=CompanyTelegramOut)
async def get_telegram_status(
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> CompanyTelegramOut:
    """Return Telegram staff bindings for this company."""
    staff_result = await session.execute(
        select(CompanyStaff)
        .where(
            CompanyStaff.company_id == company.id,
            CompanyStaff.is_active.is_(True),
            CompanyStaff.tg_chat_id.is_not(None),
        )
        .order_by(CompanyStaff.full_name)
    )
    staff_rows = staff_result.scalars().all()

    if staff_rows:
        managers = [
            TelegramManagerOut(
                tg_chat_id=s.tg_chat_id,
                full_name=s.full_name,
                telegram_username=s.telegram_username,
                role=s.role,
            )
            for s in staff_rows
            if s.tg_chat_id is not None
        ]
    else:
        result = await session.execute(
            select(CompanyManager.tg_chat_id).where(CompanyManager.company_id == company.id)
        )
        chat_ids = [row[0] for row in result.all()]
        managers = [TelegramManagerOut(tg_chat_id=cid) for cid in chat_ids]

    staff_required = await company_has_active_staff(session, company.id)
    return CompanyTelegramOut(
        connected=len(managers) > 0,
        managers=managers,
        staff_required=staff_required,
    )


@router.get("/max", response_model=CompanyMaxOut)
async def get_max_status(
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> CompanyMaxOut:
    """Return MAX messenger staff bindings for this company."""
    staff_result = await session.execute(
        select(CompanyStaff)
        .where(
            CompanyStaff.company_id == company.id,
            CompanyStaff.is_active.is_(True),
            CompanyStaff.max_user_id.is_not(None),
        )
        .order_by(CompanyStaff.full_name)
    )
    staff_rows = staff_result.scalars().all()
    managers = [
        MaxManagerOut(
            max_user_id=s.max_user_id,
            full_name=s.full_name,
            max_username=s.max_username,
            role=s.role,
        )
        for s in staff_rows
        if s.max_user_id is not None
    ]
    staff_required = await company_has_active_staff(session, company.id)
    return CompanyMaxOut(
        connected=len(managers) > 0,
        managers=managers,
        staff_required=staff_required,
    )


def _staff_response(staff: CompanyStaff) -> StaffOut:
    data = staff_out(staff)
    return StaffOut(**data)


@router.get("/staff", response_model=list[StaffOut])
async def list_company_staff(
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> list[StaffOut]:
    """List all employees registered for Telegram notifications."""
    result = await session.execute(
        select(CompanyStaff)
        .where(CompanyStaff.company_id == company.id)
        .order_by(CompanyStaff.created_at.desc())
    )
    return [_staff_response(row) for row in result.scalars().all()]


@router.post("/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
async def create_company_staff(
    payload: StaffCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> StaffOut:
    """Add an employee who may connect the Telegram bot."""
    staff_limit = staff_limit_for_plan(company.plan)
    if staff_limit is not None:
        active_count = await count_active_staff(session, company.id)
        if active_count >= staff_limit:
            upgrade_hint = (
                "Перейдите на Max для снятия лимита."
                if company.plan == "pro"
                else "Перейдите на тариф Pro или Max для увеличения лимита."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Достигнут лимит сотрудников для тарифа "
                    f"{company.plan.capitalize()} ({staff_limit}). {upgrade_hint}"
                ),
            )

    if payload.telegram_username:
        dup = await session.execute(
            select(CompanyStaff).where(
                CompanyStaff.company_id == company.id,
                func.lower(CompanyStaff.telegram_username) == payload.telegram_username,
                CompanyStaff.is_active.is_(True),
            )
        )
        if dup.scalars().first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Сотрудник с таким Telegram username уже добавлен.",
            )

    if payload.max_username:
        dup_max = await session.execute(
            select(CompanyStaff).where(
                CompanyStaff.company_id == company.id,
                func.lower(CompanyStaff.max_username) == payload.max_username,
                CompanyStaff.is_active.is_(True),
            )
        )
        if dup_max.scalars().first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Сотрудник с таким MAX username уже добавлен.",
            )

    staff = CompanyStaff(
        company_id=company.id,
        full_name=payload.full_name,
        phone=payload.phone,
        telegram_username=payload.telegram_username,
        max_username=payload.max_username,
        role=payload.role,
        notify_bookings=payload.notify_bookings,
    )
    session.add(staff)
    try:
        await session.commit()
        await session.refresh(staff)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Не удалось добавить сотрудника.",
        ) from None
    return _staff_response(staff)


@router.patch("/staff/{staff_id}", response_model=StaffOut)
async def update_company_staff(
    staff_id: uuid.UUID,
    payload: StaffUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> StaffOut:
    """Update employee details or deactivate."""
    result = await session.execute(
        select(CompanyStaff).where(
            CompanyStaff.id == staff_id,
            CompanyStaff.company_id == company.id,
        )
    )
    staff = result.scalars().first()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found.")

    if payload.full_name is not None:
        staff.full_name = payload.full_name
    if payload.phone is not None:
        staff.phone = payload.phone or None
    if payload.telegram_username is not None:
        staff.telegram_username = payload.telegram_username
    if payload.max_username is not None:
        staff.max_username = payload.max_username
    if payload.role is not None:
        staff.role = payload.role
    if payload.notify_bookings is not None:
        staff.notify_bookings = payload.notify_bookings
    if payload.is_active is not None:
        staff.is_active = payload.is_active
        if not payload.is_active:
            staff.tg_chat_id = None
            staff.max_user_id = None

    await session.commit()
    await session.refresh(staff)
    return _staff_response(staff)


@router.delete("/staff/{staff_id}")
async def delete_company_staff(
    staff_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> dict[str, str]:
    """Remove an employee from the company."""
    result = await session.execute(
        select(CompanyStaff).where(
            CompanyStaff.id == staff_id,
            CompanyStaff.company_id == company.id,
        )
    )
    staff = result.scalars().first()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found.")

    if staff.tg_chat_id is not None:
        mgr = await session.execute(
            select(CompanyManager).where(
                CompanyManager.company_id == company.id,
                CompanyManager.tg_chat_id == staff.tg_chat_id,
            )
        )
        manager_row = mgr.scalars().first()
        if manager_row is not None:
            await session.delete(manager_row)

    await session.delete(staff)
    await session.commit()
    return {"message": "Staff deleted."}


@router.get("/appointments", response_model=list[AppointmentListItem])
async def list_company_appointments(
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> list[AppointmentListItem]:
    """List all appointments for the admin's company (JWT, no API key)."""
    try:
        query = (
            select(Appointment, Client)
            .join(Client, Appointment.client_id == Client.id)
            .where(Appointment.company_id == company.id)
            .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
        )
        result = await session.execute(query)
        rows = result.all()
    except Exception:
        logger.exception("Failed to list appointments for company_id=%s", company.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load appointments.",
        ) from None

    return [
        AppointmentListItem(
            id=appointment.id,
            client_name=client.full_name,
            client_phone=client.phone,
            service_name=appointment.service_name,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            status=appointment.status,
        )
        for appointment, client in rows
    ]


@router.post(
    "/appointments",
    response_model=AppointmentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company_appointment_endpoint(
    payload: AppointmentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> AppointmentCreateResponse:
    """Create a booking from the admin calendar."""
    try:
        client, appointment = await create_company_appointment(
            session,
            company=company,
            full_name=payload.full_name,
            phone=payload.phone,
            service_name=payload.service_name,
            appointment_date=payload.appointment_date,
            appointment_time=payload.appointment_time,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create appointment for company_id=%s", company.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create appointment.",
        ) from None

    return AppointmentCreateResponse(
        appointment_id=appointment.id,
        client_id=client.id,
    )


@router.patch("/appointments/{appointment_id}/status")
async def update_company_appointment_status(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    company: Company = Depends(get_current_admin_company),
) -> dict[str, str]:
    """Update appointment status from the admin cabinet."""
    result = await session.execute(
        select(Appointment, Client)
        .join(Client, Appointment.client_id == Client.id)
        .where(
            Appointment.id == appointment_id,
            Appointment.company_id == company.id,
        )
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    appointment, client = row
    previous_status = appointment.status
    appointment.status = payload.status
    await session.commit()

    if (
        payload.status == AppointmentStatus.CANCELLED
        and previous_status != AppointmentStatus.CANCELLED
    ):
        context = build_appointment_context(
            client_name=client.full_name,
            company_name=company.name,
            service_name=appointment.service_name,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
        )
        cancel_text, enabled = await get_template_text(
            company.id, "booking_cancelled", context=context
        )
        if enabled and cancel_text:
            try:
                await notify_client(
                    client.phone,
                    cancel_text,
                    max_user_id=client.max_user_id,
                )
            except Exception:
                logger.exception(
                    "Failed to send cancellation notification for appointment_id=%s",
                    appointment_id,
                )

    return {"message": "Status updated successfully"}
