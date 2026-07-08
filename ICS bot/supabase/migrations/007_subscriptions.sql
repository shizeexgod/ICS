-- Trial / Pro subscription fields on companies.
-- Safe to re-run (idempotent).

ALTER TABLE public.companies
    ADD COLUMN IF NOT EXISTS plan VARCHAR(20) NOT NULL DEFAULT 'trial',
    ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS reminders_used INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS reminders_period_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS pro_price_rub INTEGER NOT NULL DEFAULT 4000;

COMMENT ON COLUMN public.companies.plan IS 'trial | pro';
COMMENT ON COLUMN public.companies.trial_ends_at IS 'Trial expiry (10 days from onboarding).';
COMMENT ON COLUMN public.companies.reminders_used IS 'Reminders sent in current billing period (trial cap: 100).';
COMMENT ON COLUMN public.companies.pro_price_rub IS 'Pro plan price in RUB (default 4000).';

-- Backfill trial end for companies created before this migration.
UPDATE public.companies
SET trial_ends_at = created_at + interval '10 days'
WHERE trial_ends_at IS NULL AND plan = 'trial';

UPDATE public.companies
SET reminders_period_start = date_trunc('month', now())
WHERE reminders_period_start IS NULL;
