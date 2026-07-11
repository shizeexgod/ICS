-- Company staff: pre-registered employees who receive Telegram notifications.
-- Admins add staff in the dashboard (name, phone, @username); the bot binds
-- tg_chat_id only when the Telegram username matches a staff record.

CREATE TABLE IF NOT EXISTS public.company_staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(32),
    telegram_username VARCHAR(64),
    role VARCHAR(32) NOT NULL DEFAULT 'manager',
    notify_bookings BOOLEAN NOT NULL DEFAULT TRUE,
    tg_chat_id BIGINT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_company_staff_company_id
    ON public.company_staff(company_id);

CREATE INDEX IF NOT EXISTS idx_company_staff_tg_chat_id
    ON public.company_staff(tg_chat_id)
    WHERE tg_chat_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_company_staff_company_username
    ON public.company_staff(company_id, lower(telegram_username))
    WHERE telegram_username IS NOT NULL AND telegram_username <> '';

COMMENT ON TABLE public.company_staff IS
    'Pre-registered company employees for Telegram admin notifications.';
