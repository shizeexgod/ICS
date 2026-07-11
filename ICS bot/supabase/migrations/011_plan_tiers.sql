-- 3-tier plan support: trial (10 days) | pro | max, with real monthly/annual
-- billing periods and expiry tracking. Safe to re-run (idempotent).

ALTER TABLE public.companies
    ADD COLUMN IF NOT EXISTS billing_period VARCHAR(10) NOT NULL DEFAULT 'monthly',
    ADD COLUMN IF NOT EXISTS subscription_ends_at TIMESTAMPTZ;

COMMENT ON COLUMN public.companies.plan IS 'trial | pro | max';
COMMENT ON COLUMN public.companies.trial_ends_at IS 'Trial expiry (10 days from onboarding).';
COMMENT ON COLUMN public.companies.billing_period IS 'monthly | annual — period of the current paid subscription.';
COMMENT ON COLUMN public.companies.subscription_ends_at IS 'Paid subscription expiry. NULL = no active paid subscription.';
COMMENT ON COLUMN public.companies.pro_price_rub IS 'Price in RUB of the current plan/period (display + billing default).';

ALTER TABLE public.company_payments
    ADD COLUMN IF NOT EXISTS plan VARCHAR(10) NOT NULL DEFAULT 'pro',
    ADD COLUMN IF NOT EXISTS billing_period VARCHAR(10) NOT NULL DEFAULT 'monthly';

COMMENT ON COLUMN public.company_payments.plan IS 'pro | max — plan purchased by this payment.';
COMMENT ON COLUMN public.company_payments.billing_period IS 'monthly | annual — billing period purchased by this payment.';

-- Backfill: existing trial companies get the new 10-day window from creation.
UPDATE public.companies
SET trial_ends_at = created_at + interval '10 days'
WHERE plan = 'trial';

-- Backfill: existing paying companies (legacy "pro" with no end date) keep
-- access uninterrupted — give them a subscription window starting now.
UPDATE public.companies
SET subscription_ends_at = now() + interval '30 days'
WHERE plan IN ('pro', 'max') AND subscription_status = 'active' AND subscription_ends_at IS NULL;
