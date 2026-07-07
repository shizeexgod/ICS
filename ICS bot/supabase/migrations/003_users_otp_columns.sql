-- Extend existing `users` table for OTP login (personal cabinet).
-- Safe to run if columns already exist (uses IF NOT EXISTS pattern via DO block).

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS otp_secret VARCHAR(128),
    ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Ensure phone uniqueness for OTP lookup (skip if constraint already exists).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'users_phone_key'
    ) THEN
        ALTER TABLE public.users ADD CONSTRAINT users_phone_key UNIQUE (phone);
    END IF;
END $$;
