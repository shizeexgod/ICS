"""End-to-end smoke test for the multi-tenant booking flow."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import uuid

import httpx
from sqlalchemy import select, text

from app.bot.handlers import _bind_manager
from app.core.database import AsyncSessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.company import Company
from app.models.company_manager import CompanyManager
from app.services.notifications import send_client_sms, send_client_whatsapp
from app.services.scheduler import schedule_appointment_reminder
from app.services.telegram_notifications import get_manager_chat_ids

BASE_URL = "http://127.0.0.1:8000"
TEST_CHAT_ID = 999888777  # synthetic id — Telegram send will fail, but DB flow is verified


async def run() -> None:
    print("=" * 60)
    print("1. Health check")
    async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
        r = await client.get(f"{BASE_URL}/health")
        print(f"   status={r.status_code} body={r.json()}")

    print("\n2. Load test company from DB")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.name == "Test_Barber")
        )
        company = result.scalars().first()
        if company is None:
            result = await session.execute(select(Company).limit(1))
            company = result.scalars().first()
        assert company is not None, "No companies in DB — create one first"
        api_key = company.api_key
        company_id = company.id
        print(f"   company={company.name!r} id={company_id} api_key={api_key!r}")

    print("\n3. Bind synthetic manager chat (simulates /start <api_key>)")
    bound, bind_error = await _bind_manager(api_key=api_key, tg_chat_id=TEST_CHAT_ID)
    assert bind_error is None, f"Manager bind error: {bind_error}"
    assert bound is not None, "Manager bind failed — api_key not found"
    print(f"   bound tg_chat_id={TEST_CHAT_ID} -> {bound.name}")

    async with AsyncSessionLocal() as session:
        chat_ids = await get_manager_chat_ids(session, company_id)
        print(f"   managers in DB for company: {chat_ids}")

    print("\n4. POST /webhook/tilda — create booking")
    tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    payload = {
        "full_name": "Тест Клиент",
        "phone": "+7 (900) 111-22-33",
        "service_name": "Стрижка",
        "appointment_date": tomorrow,
        "appointment_time": "15:30:00",
        "api_key": api_key,
    }
    async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
        r = await client.post(
            f"{BASE_URL}/webhook/tilda",
            json=payload,
            headers={"X-API-Key": api_key},
        )
        print(f"   HTTP {r.status_code}")
        body = r.json()
        print(f"   response={json.dumps(body, ensure_ascii=False, default=str)}")
        assert r.status_code == 201, body
        appointment_id = uuid.UUID(str(body["appointment_id"]))

    print("\n5. Verify appointment in DB")
    async with AsyncSessionLocal() as session:
        appt = await session.get(Appointment, appointment_id)
        assert appt is not None
        assert appt.status == AppointmentStatus.PENDING
        assert appt.company_id == company_id
        print(f"   appointment_id={appt.id} status={appt.status.value} service={appt.service_name!r}")

    print("\n6. Confirm booking (simulates inline button callback)")
    async with AsyncSessionLocal() as session:
        appt = await session.get(Appointment, appointment_id)
        assert appt is not None
        appt.status = AppointmentStatus.CONFIRMED
        await session.commit()
        print(f"   status updated -> {AppointmentStatus.CONFIRMED.value}")

    print("\n7. Dry-run client notifications (no Green-API / SMS.ru keys)")
    wa_ok = await send_client_whatsapp("79001112233", "Тест подтверждения записи")
    sms_ok = await send_client_sms("79001112233", "Тест подтверждения записи")
    print(f"   whatsapp dry-run ok={wa_ok}, sms dry-run ok={sms_ok}")

    print("\n8. Schedule reminder (2h before visit)")
    appt_dt = dt.datetime.combine(
        dt.date.fromisoformat(tomorrow), dt.time(15, 30)
    )
    schedule_appointment_reminder(appointment_id, appt_dt)
    print(f"   reminder scheduled for {appt_dt - dt.timedelta(hours=2)}")

    print("\n9. Cleanup test manager binding")
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "DELETE FROM company_managers WHERE tg_chat_id = :cid AND company_id = :co"
            ),
            {"cid": TEST_CHAT_ID, "co": str(company_id)},
        )
        await session.commit()
        print("   synthetic manager removed")

    print("\n" + "=" * 60)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(run())
