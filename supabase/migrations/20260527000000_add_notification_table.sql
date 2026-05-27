-- ============================================================
-- Migration: In-App-Benachrichtigungen für Event-Edit/Cancel/Neue Teilnehmer
--
-- - notification: Pro Empfänger ein Eintrag mit Typ, Payload (jsonb), Read-State.
--   Wird vom Backend (Service-Role) bei update_event / delete_event / rsvp(Accept)
--   befüllt. Empfänger lesen ihre eigene Liste über RLS.
-- ============================================================

CREATE TABLE public.notification (
    notification_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_person_id  UUID NOT NULL REFERENCES public.person(person_id) ON DELETE CASCADE,
    event_id             UUID REFERENCES public.event(event_id) ON DELETE CASCADE,
    type                 TEXT NOT NULL
                          CHECK (type IN ('event_updated', 'event_cancelled', 'new_participant')),
    payload              JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at              TIMESTAMPTZ
);

CREATE INDEX idx_notification_recipient_unread
    ON public.notification (recipient_person_id, created_at DESC)
    WHERE read_at IS NULL;

CREATE INDEX idx_notification_recipient_all
    ON public.notification (recipient_person_id, created_at DESC);

ALTER TABLE public.notification ENABLE ROW LEVEL SECURITY;

-- Empfänger darf seine eigenen Benachrichtigungen lesen
CREATE POLICY "select_own_notification" ON public.notification
    FOR SELECT TO authenticated
    USING (
        recipient_person_id = (
            SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid()
        )
    );

-- Empfänger darf nur read_at seiner eigenen Benachrichtigungen aktualisieren
CREATE POLICY "update_own_notification_read" ON public.notification
    FOR UPDATE TO authenticated
    USING (
        recipient_person_id = (
            SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid()
        )
    )
    WITH CHECK (
        recipient_person_id = (
            SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid()
        )
    );

-- Kein INSERT-Policy für authenticated → nur Backend (Service-Role) erstellt Einträge.
-- Kein DELETE-Policy → wird über ON DELETE CASCADE der person/event-FKs aufgeräumt.
