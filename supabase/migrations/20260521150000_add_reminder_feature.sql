-- ============================================================
-- Migration: Erinnerungen vor Eventbeginn (Anforderung K4)
--
-- - reminder_preference: pro Person ein Setting (enabled, lead_time_minutes)
-- - web_push_subscription: Browser-Push-Subscriptions (Endpoint + Keys)
-- - reminder_sent: Idempotenz-Tracking, damit pro (event, person) nur einmal
--   gesendet wird
-- ============================================================

-- ─── 1. reminder_preference ─────────────────────────────────────────────────

CREATE TABLE public.reminder_preference (
    person_id          UUID PRIMARY KEY REFERENCES public.person(person_id) ON DELETE CASCADE,
    enabled            BOOLEAN NOT NULL DEFAULT false,
    lead_time_minutes  INTEGER NOT NULL DEFAULT 60
                       CHECK (lead_time_minutes BETWEEN 1 AND 10080),  -- 1 min .. 7 Tage
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.reminder_preference ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own_reminder_preference" ON public.reminder_preference
    FOR SELECT TO authenticated
    USING (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

CREATE POLICY "insert_own_reminder_preference" ON public.reminder_preference
    FOR INSERT TO authenticated
    WITH CHECK (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

CREATE POLICY "update_own_reminder_preference" ON public.reminder_preference
    FOR UPDATE TO authenticated
    USING (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

CREATE POLICY "delete_own_reminder_preference" ON public.reminder_preference
    FOR DELETE TO authenticated
    USING (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

-- ─── 2. web_push_subscription ──────────────────────────────────────────────

CREATE TABLE public.web_push_subscription (
    web_push_subscription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id                UUID NOT NULL REFERENCES public.person(person_id) ON DELETE CASCADE,
    endpoint                 TEXT NOT NULL,
    p256dh_key               TEXT NOT NULL,
    auth_key                 TEXT NOT NULL,
    user_agent               TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (person_id, endpoint)
);

CREATE INDEX idx_web_push_subscription_person ON public.web_push_subscription(person_id);

ALTER TABLE public.web_push_subscription ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own_web_push_subscription" ON public.web_push_subscription
    FOR SELECT TO authenticated
    USING (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

CREATE POLICY "insert_own_web_push_subscription" ON public.web_push_subscription
    FOR INSERT TO authenticated
    WITH CHECK (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

CREATE POLICY "delete_own_web_push_subscription" ON public.web_push_subscription
    FOR DELETE TO authenticated
    USING (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

-- ─── 3. reminder_sent (Idempotenz) ─────────────────────────────────────────
-- Wird ausschliesslich vom Server-Scheduler beschrieben (Service-Role-Key).
-- Kein RLS-Schreibrecht für authenticated.

CREATE TABLE public.reminder_sent (
    event_id   UUID NOT NULL REFERENCES public.event(event_id) ON DELETE CASCADE,
    person_id  UUID NOT NULL REFERENCES public.person(person_id) ON DELETE CASCADE,
    sent_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, person_id)
);

ALTER TABLE public.reminder_sent ENABLE ROW LEVEL SECURITY;
-- Kein Policy für authenticated → Tabelle ist für Endnutzer unsichtbar.
-- Der Backend-Scheduler nutzt den Service-Role-Key und umgeht RLS.
