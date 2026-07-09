"""Application configuration loaded from environment variables (.env)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings, populated from the process environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Database ---------------------------------------------------------
    DATABASE_URL: str = Field(
        ...,
        description="Async SQLAlchemy connection string to the Supabase Postgres instance.",
    )

    # --- Telegram -----------------------------------------------------------
    TELEGRAM_BOT_TOKEN: str = Field(
        ...,
        description="Bot token issued by @BotFather.",
    )

    # --- Client notification channels (WhatsApp / SMS) -----------------------
    GREEN_API_INSTANCE: str = Field(
        default="",
        description="Green-API instance id (waInstanceXXXXX) used to send WhatsApp messages.",
    )
    GREEN_API_TOKEN: str = Field(
        default="",
        description="Green-API auth token, paired with GREEN_API_INSTANCE.",
    )
    SMS_RU_API_KEY: str = Field(
        default="",
        description="SMS.ru api_id used to send SMS reminders/confirmations to clients.",
    )

    # --- API / Security -------------------------------------------------------
    # NOTE: per-tenant API keys are now stored in the `companies.api_key` database
    # column and validated against the incoming request in the webhook handler.
    # This legacy global secret is kept optional for backward compatibility only.
    API_SECRET_KEY: str = Field(
        default="",
        description="Deprecated global webhook secret, superseded by per-company API keys.",
    )

    # --- HTTP / CORS --------------------------------------------------------
    CORS_ORIGINS: str = Field(
        default="*",
        description=(
            "Comma-separated browser origins allowed to call this API "
            "(e.g. https://your-site.vercel.app). Use * for local dev only."
        ),
    )

    # --- Misc ---------------------------------------------------------------
    ENVIRONMENT: str = Field(default="local")

    # --- JWT (personal cabinet auth) ----------------------------------------
    JWT_SECRET: str = Field(
        default="change-me-in-production",
        description="Secret key used to sign JWT access tokens for end-users.",
    )
    JWT_EXPIRE_DAYS: int = Field(
        default=30,
        description="JWT access token lifetime in days.",
    )

    # --- Supabase REST (PostgREST client for auth/templates) ----------------
    SUPABASE_URL: str = Field(
        default="",
        description="Supabase project URL, e.g. https://xxxx.supabase.co",
    )
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        default="",
        description="Service role key for server-side Supabase table access.",
    )

    # --- SMTP (email OTP) ---------------------------------------------------
    SMTP_SERVER: str = Field(default="", description="SMTP host for verification emails.")
    SMTP_PORT: int = Field(default=587, description="SMTP port (usually 587 with STARTTLS).")
    SMTP_USER: str = Field(default="", description="SMTP login / From address.")
    SMTP_PASSWORD: str = Field(default="", description="SMTP password or app password.")

    # --- YooKassa (Pro subscription billing) --------------------------------
    YOOKASSA_SHOP_ID: str = Field(
        default="",
        description="YooKassa shop id (merchant id).",
    )
    YOOKASSA_SECRET_KEY: str = Field(
        default="",
        description="YooKassa secret key for API and webhooks.",
    )
    YOOKASSA_RETURN_URL: str = Field(
        default="",
        description="Default return URL after payment (frontend cabinet page).",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def _ensure_async_driver(cls, value: str) -> str:
        """Normalize plain postgres URLs to use the asyncpg driver."""
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list for CORSMiddleware."""
        raw = self.CORS_ORIGINS.strip()
        if not raw or raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    return Settings()  # type: ignore[call-arg]


settings: Settings = get_settings()
