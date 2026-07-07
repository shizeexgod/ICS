-- Multi-tenant admin binding: maps Telegram chat ids to companies.
-- Run this in the Supabase SQL Editor (Dashboard -> SQL -> New query).

CREATE TABLE IF NOT EXISTS public.company_managers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID NOT NULL REFERENCES public.companies (id) ON DELETE CASCADE,
    tg_chat_id  BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_company_managers_company_id
    ON public.company_managers (company_id);

CREATE INDEX IF NOT EXISTS idx_company_managers_tg_chat_id
    ON public.company_managers (tg_chat_id);

-- Prevent duplicate bindings for the same (company, chat) pair.
CREATE UNIQUE INDEX IF NOT EXISTS uq_company_managers_company_chat
    ON public.company_managers (company_id, tg_chat_id);

COMMENT ON TABLE public.company_managers IS
    'Telegram admins/managers subscribed to a company''s booking notifications.';
