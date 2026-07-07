-- Full ICS SaaS schema for Supabase (companies, clients, appointments, managers, users).
-- Safe to run on a fresh project. On an existing DB, prefer individual migrations 001/002.

-- ---------------------------------------------------------------------------
-- companies
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.companies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    owner_email VARCHAR(255) NOT NULL,
    api_key     VARCHAR(64) NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_companies_api_key ON public.companies (api_key);

-- ---------------------------------------------------------------------------
-- clients (per-company customers)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.clients (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id          UUID NOT NULL REFERENCES public.companies (id) ON DELETE CASCADE,
    full_name           VARCHAR(255) NOT NULL,
    phone               VARCHAR(32) NOT NULL,
    email               VARCHAR(255),
    tg_user_id          BIGINT,
    preferred_messenger VARCHAR(32) NOT NULL DEFAULT 'telegram',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_clients_company_id ON public.clients (company_id);
CREATE INDEX IF NOT EXISTS idx_clients_phone ON public.clients (phone);
CREATE INDEX IF NOT EXISTS idx_clients_tg_user_id ON public.clients (tg_user_id);

-- ---------------------------------------------------------------------------
-- appointments
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.appointments (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id       UUID NOT NULL REFERENCES public.companies (id) ON DELETE CASCADE,
    client_id        UUID NOT NULL REFERENCES public.clients (id) ON DELETE CASCADE,
    service_name     VARCHAR(255) NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    price            NUMERIC(10, 2) NOT NULL DEFAULT 0,
    status           VARCHAR(32) NOT NULL DEFAULT 'scheduled',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_appointments_company_id ON public.appointments (company_id);
CREATE INDEX IF NOT EXISTS idx_appointments_client_id ON public.appointments (client_id);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON public.appointments (status);

-- ---------------------------------------------------------------------------
-- company_managers (Telegram admin bindings)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.company_managers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID NOT NULL REFERENCES public.companies (id) ON DELETE CASCADE,
    tg_chat_id  BIGINT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_company_managers_company_id
    ON public.company_managers (company_id);
CREATE INDEX IF NOT EXISTS idx_company_managers_tg_chat_id
    ON public.company_managers (tg_chat_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_company_managers_company_chat
    ON public.company_managers (company_id, tg_chat_id);

-- ---------------------------------------------------------------------------
-- users (website personal cabinet)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone           VARCHAR(32) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    otp_secret      VARCHAR(128),
    otp_expires_at  TIMESTAMPTZ,
    telegram_id     BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_phone ON public.users (phone);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON public.users (telegram_id);

-- ---------------------------------------------------------------------------
-- optional: notification audit log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id  UUID NOT NULL REFERENCES public.appointments (id) ON DELETE CASCADE,
    channel_used    VARCHAR(32) NOT NULL,
    message_text    TEXT NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'pending',
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_appointment_id
    ON public.notifications (appointment_id);
