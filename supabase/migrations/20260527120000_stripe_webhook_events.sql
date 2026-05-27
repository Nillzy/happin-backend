-- Persistent Stripe webhook inbox with processing status and retry tracking.

CREATE TYPE public.stripe_webhook_status AS ENUM ('pending', 'processing', 'success', 'failed');

CREATE TABLE public.stripe_webhook_event (
    webhook_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_event_id text NOT NULL UNIQUE,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    status public.stripe_webhook_status NOT NULL DEFAULT 'pending',
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts integer NOT NULL DEFAULT 5 CHECK (max_attempts > 0),
    last_error text,
    processed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_stripe_webhook_event_status ON public.stripe_webhook_event(status);
CREATE INDEX idx_stripe_webhook_event_type ON public.stripe_webhook_event(event_type);
CREATE INDEX idx_stripe_webhook_event_created_at ON public.stripe_webhook_event(created_at DESC);

ALTER TABLE public.stripe_webhook_event ENABLE ROW LEVEL SECURITY;
