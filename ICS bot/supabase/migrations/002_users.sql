-- End-user accounts for the website personal cabinet (OTP login).
-- Run in Supabase SQL Editor: Dashboard -> SQL -> New query.

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

COMMENT ON TABLE public.users IS
    'End-user accounts for website/bot auth (phone + OTP).';
