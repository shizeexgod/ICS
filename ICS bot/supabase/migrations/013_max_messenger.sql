-- MAX messenger: staff + client chat bindings (parallel to Telegram tg_chat_id).

ALTER TABLE public.company_staff
    ADD COLUMN IF NOT EXISTS max_user_id BIGINT,
    ADD COLUMN IF NOT EXISTS max_username VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_company_staff_max_user_id
    ON public.company_staff(max_user_id)
    WHERE max_user_id IS NOT NULL;

ALTER TABLE public.clients
    ADD COLUMN IF NOT EXISTS max_user_id BIGINT;

CREATE INDEX IF NOT EXISTS idx_clients_max_user_id
    ON public.clients(max_user_id)
    WHERE max_user_id IS NOT NULL;
