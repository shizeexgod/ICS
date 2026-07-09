"""
Application entry point.

Runs the FastAPI HTTP server and the aiogram Telegram bot (long-polling) side by
side inside the same asyncio event loop, using FastAPI's lifespan events to
start/stop the bot together with the API server.

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import sys

# On Windows the default ProactorEventLoop breaks aiogram long-polling when
# combined with FastAPI/uvicorn in the same process. Selector policy is required.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.billing import router as billing_v1_router
from app.api.v1.auth import router as auth_v1_router
from app.api.v1.company import router as company_v1_router
from app.api.v1.templates import router as templates_v1_router
from app.api.appointments import router as appointments_router
from app.api.bookings import router as bookings_router
from app.api.webhooks import router as webhooks_router
from app.bot.main import start_bot_polling, stop_bot_polling
from app.core.config import settings
from app.core.database import check_database_connection
from app.services.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start the Telegram bot polling task alongside the API server, and stop it on shutdown."""
    logger.info("Starting up ICS bot service (environment=%s)...", settings.ENVIRONMENT)

    if not await check_database_connection():
        logger.warning("Database connectivity check failed; continuing startup anyway.")

    await start_bot_polling()
    logger.info("Telegram bot polling started.")

    start_scheduler()
    logger.info("Appointment reminder scheduler started.")

    try:
        yield
    finally:
        logger.info("Shutting down ICS bot service...")
        shutdown_scheduler()
        await stop_bot_polling()
        logger.info("Telegram bot polling stopped.")


app = FastAPI(
    title="ICS Bot Service",
    description="FastAPI webhook layer + aiogram v3 Telegram bot for the ICS booking system.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS must be registered before any routes so browser clients (Vercel frontend,
# local dev, ngrok tunnel) can call this API from another origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks_router)
app.include_router(auth_v1_router)
app.include_router(company_v1_router)
app.include_router(templates_v1_router)
app.include_router(billing_v1_router)
app.include_router(bookings_router)
app.include_router(appointments_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Simple liveness endpoint for uptime monitors / load balancers."""
    db_ok = await check_database_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_ok else "unreachable",
    }


if __name__ == "__main__":
    import os
    from pathlib import Path

    import uvicorn

    # When started as `python ICS bot/main.py` from repo root, ensure imports/cwd
    # resolve to the backend directory (same layout as local dev).
    backend_root = Path(__file__).resolve().parent
    os.chdir(backend_root)

    # Hard-bind to containerPort from amvera.yaml. Do NOT override with PORT=80.
    port = 5000

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
