-- Update plan defaults: Trial 7 days, Pro 5000 RUB.
-- Safe to re-run.

COMMENT ON COLUMN public.companies.trial_ends_at IS 'Trial expiry (7 days from onboarding).';
COMMENT ON COLUMN public.companies.pro_price_rub IS 'Pro plan price in RUB (default 5000).';

UPDATE public.companies
SET pro_price_rub = 5000
WHERE pro_price_rub = 4000;
