-- YooKassa payment records for Pro subscriptions.
-- Safe to re-run (idempotent).

CREATE TABLE IF NOT EXISTS public.company_payments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id          UUID NOT NULL REFERENCES public.companies (id) ON DELETE CASCADE,
    yookassa_payment_id VARCHAR(64) NOT NULL UNIQUE,
    amount_rub          INTEGER NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at             TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_company_payments_company_id
    ON public.company_payments (company_id);

CREATE INDEX IF NOT EXISTS idx_company_payments_status
    ON public.company_payments (status);

COMMENT ON TABLE public.company_payments IS
    'YooKassa payment attempts for ICS Pro subscription upgrades.';
