-- Email OTP auth + Telegram notification templates
-- Run in Supabase SQL Editor: Dashboard -> SQL -> New query
-- Safe to re-run: uses IF NOT EXISTS / conditional alters where possible.

-- ---------------------------------------------------------------------------
-- email_verifications — one-time login codes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.email_verifications (
    id          BIGSERIAL PRIMARY KEY,
    email       VARCHAR(255) NOT NULL UNIQUE,
    code        VARCHAR(4)   NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ  NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_email_verifications_email
    ON public.email_verifications (email);

CREATE INDEX IF NOT EXISTS idx_email_verifications_expires_at
    ON public.email_verifications (expires_at);

COMMENT ON TABLE public.email_verifications IS
    'Temporary 4-digit email OTP codes for ICS login (upserted by email).';

-- ---------------------------------------------------------------------------
-- users — rebuild for email-based auth (replaces phone/OTP columns)
-- ---------------------------------------------------------------------------
-- If the legacy phone-based table exists, migrate in place.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'phone'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'email'
    ) THEN
        ALTER TABLE public.users
            ADD COLUMN email      VARCHAR(255),
            ADD COLUMN tg_chat_id VARCHAR(50),
            ADD COLUMN company_id UUID REFERENCES public.companies (id) ON DELETE CASCADE,
            ADD COLUMN role       VARCHAR(20) NOT NULL DEFAULT 'client';

        -- Legacy phone-auth rows cannot be migrated automatically.
        DELETE FROM public.users WHERE email IS NULL;

        ALTER TABLE public.users
            DROP COLUMN IF EXISTS phone,
            DROP COLUMN IF EXISTS name,
            DROP COLUMN IF EXISTS otp_secret,
            DROP COLUMN IF EXISTS otp_expires_at,
            DROP COLUMN IF EXISTS telegram_id;

        ALTER TABLE public.users
            ALTER COLUMN email SET NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email ON public.users (email);
    END IF;
END $$;

-- Fresh install (no legacy users table)
CREATE TABLE IF NOT EXISTS public.users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) NOT NULL UNIQUE,
    tg_chat_id  VARCHAR(50),
    company_id  UUID REFERENCES public.companies (id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL DEFAULT 'client',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users (email);
CREATE INDEX IF NOT EXISTS idx_users_company_id ON public.users (company_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users (role);

COMMENT ON TABLE public.users IS
    'ICS accounts: email login, optional Telegram chat binding, tenant + role.';

-- ---------------------------------------------------------------------------
-- notification_templates — per-company Telegram message templates
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.notification_templates (
    id          BIGSERIAL PRIMARY KEY,
    company_id  UUID         NOT NULL REFERENCES public.companies (id) ON DELETE CASCADE,
    event_type  VARCHAR(50)  NOT NULL,
    tg_template TEXT         NOT NULL,
    is_enabled  BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_notification_templates_company_event
        UNIQUE (company_id, event_type)
);

CREATE INDEX IF NOT EXISTS idx_notification_templates_company_id
    ON public.notification_templates (company_id);

CREATE INDEX IF NOT EXISTS idx_notification_templates_event_type
    ON public.notification_templates (event_type);

COMMENT ON TABLE public.notification_templates IS
    'Admin-configurable Telegram templates per company and event type.';
