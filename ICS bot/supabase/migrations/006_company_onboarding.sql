-- Enterprise onboarding: companies tenant table + users.company_id / users.role
-- Safe to re-run on Supabase (idempotent).
-- Run after 004_email_auth_notifications.sql and 005_user_profile_fields.sql.

-- ---------------------------------------------------------------------------
-- companies — tenant businesses (API key per company)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.companies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    owner_email VARCHAR(255) NOT NULL,
    api_key     VARCHAR(64) NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_companies_api_key ON public.companies (api_key);

COMMENT ON TABLE public.companies IS
    'ICS tenant: one row per service business; api_key used for webhooks and CRM.';

-- ---------------------------------------------------------------------------
-- users — link accounts to a company + role (client | admin)
-- ---------------------------------------------------------------------------
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES public.companies (id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'client';

CREATE INDEX IF NOT EXISTS idx_users_company_id ON public.users (company_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users (role);

COMMENT ON COLUMN public.users.company_id IS
    'NULL until POST /api/v1/company/setup completes onboarding.';
COMMENT ON COLUMN public.users.role IS
    'client = end-user; admin = company owner after onboarding.';
