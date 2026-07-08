-- Profile fields for email registration flow
ALTER TABLE public.email_verifications
    ADD COLUMN IF NOT EXISTS name  VARCHAR(255),
    ADD COLUMN IF NOT EXISTS phone VARCHAR(32);

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS name  VARCHAR(255),
    ADD COLUMN IF NOT EXISTS phone VARCHAR(32);

COMMENT ON COLUMN public.users.name IS 'Display name collected at registration.';
COMMENT ON COLUMN public.users.phone IS 'Optional contact phone, not used for login.';
