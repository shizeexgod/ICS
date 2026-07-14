-- Referral program: company codes, first-purchase discount, referrer balance.

ALTER TABLE public.companies
    ADD COLUMN IF NOT EXISTS referral_code VARCHAR(16),
    ADD COLUMN IF NOT EXISTS referred_by_company_id UUID REFERENCES public.companies(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS referral_balance_rub INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS referral_discount_used BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_referral_code
    ON public.companies(referral_code)
    WHERE referral_code IS NOT NULL AND referral_code <> '';

ALTER TABLE public.company_payments
    ADD COLUMN IF NOT EXISTS original_amount_rub INTEGER,
    ADD COLUMN IF NOT EXISTS discount_rub INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS referrer_company_id UUID REFERENCES public.companies(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS referral_reward_applied BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN public.companies.referral_code IS 'Shareable promo code for inviting other companies.';
COMMENT ON COLUMN public.companies.referral_balance_rub IS 'Accrued referral rewards in RUB (20% of referred first payments).';
COMMENT ON COLUMN public.companies.referral_discount_used IS 'True after the company used a referral discount on first paid subscription.';
