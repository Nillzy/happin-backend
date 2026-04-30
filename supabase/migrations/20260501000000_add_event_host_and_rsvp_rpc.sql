-- Migration: Separate event_host table + RSVP RPC
-- Reason: event_participation previously stored both hosts and guests (role='Host'/'Participant'),
-- making RSVP upsert logic fragile. Separating hosts into their own table
-- simplifies RSVP and makes the data model cleaner.

-- ─── 1. Create event_host table ───────────────────────────────────────────────

CREATE TABLE public.event_host (
    event_host_id UUID         DEFAULT gen_random_uuid() PRIMARY KEY,
    event_id      UUID         NOT NULL REFERENCES public.event(event_id)   ON DELETE CASCADE,
    person_id     UUID         NOT NULL REFERENCES public.person(person_id)  ON DELETE CASCADE,
    created_at    TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, person_id)
);

-- ─── 2. Migrate existing host entries ─────────────────────────────────────────

INSERT INTO public.event_host (event_id, person_id, created_at)
SELECT event_id, person_id, created_at
FROM   public.event_participation
WHERE  role = 'Host';

DELETE FROM public.event_participation WHERE role = 'Host';

-- ─── 2b. Update RLS policies that depend on event_participation.role ──────────
-- These policies used role='Host' to verify host identity.
-- They are replaced with equivalent checks via the new event_host table.

DROP POLICY IF EXISTS "host_update_events"          ON public.event;
DROP POLICY IF EXISTS "host_update_locations"        ON public.location;
DROP POLICY IF EXISTS "host_insert_ticket_options"   ON public.ticket_option;
DROP POLICY IF EXISTS "host_update_ticket_options"   ON public.ticket_option;
DROP POLICY IF EXISTS "host_delete_ticket_options"   ON public.ticket_option;

CREATE POLICY "host_update_events" ON public.event
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM   public.event_host eh
            JOIN   public.person p ON p.person_id = eh.person_id
            WHERE  eh.event_id = event.event_id
              AND  p.supabase_user_id = auth.uid()
        )
    );

CREATE POLICY "host_update_locations" ON public.location
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM   public.event e
            JOIN   public.event_host eh ON eh.event_id = e.event_id
            JOIN   public.person p ON p.person_id = eh.person_id
            WHERE  e.location_id = location.location_id
              AND  p.supabase_user_id = auth.uid()
        )
    );

CREATE POLICY "host_insert_ticket_options" ON public.ticket_option
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM   public.event_host eh
            JOIN   public.person p ON p.person_id = eh.person_id
            WHERE  eh.event_id = ticket_option.event_id
              AND  p.supabase_user_id = auth.uid()
        )
    );

CREATE POLICY "host_update_ticket_options" ON public.ticket_option
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM   public.event_host eh
            JOIN   public.person p ON p.person_id = eh.person_id
            WHERE  eh.event_id = ticket_option.event_id
              AND  p.supabase_user_id = auth.uid()
        )
    );

CREATE POLICY "host_delete_ticket_options" ON public.ticket_option
    FOR DELETE TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM   public.event_host eh
            JOIN   public.person p ON p.person_id = eh.person_id
            WHERE  eh.event_id = ticket_option.event_id
              AND  p.supabase_user_id = auth.uid()
        )
    );

-- Now safe to drop the role column and its enum type.
ALTER TABLE public.event_participation DROP COLUMN role;

DROP TYPE IF EXISTS public.event_role_enum;

-- ─── 3. RLS for event_host ────────────────────────────────────────────────────

ALTER TABLE public.event_host ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_event_host"
    ON public.event_host FOR SELECT USING (true);

CREATE POLICY "insert_event_host"
    ON public.event_host FOR INSERT TO authenticated WITH CHECK (true);

GRANT SELECT              ON public.event_host TO anon;
GRANT SELECT, INSERT      ON public.event_host TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.event_host TO service_role;

-- ─── 4. RPC: race-condition-safe RSVP ─────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.rsvp_to_event(
    p_event_id  UUID,
    p_person_id UUID,
    p_status    public.invitation_status_enum
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_event          RECORD;
    v_accepted_count INTEGER;
BEGIN
    -- Row-level lock serialises concurrent RSVPs for the same event,
    -- preventing race conditions when the last seat is claimed.
    SELECT * INTO v_event
    FROM   public.event
    WHERE  event_id = p_event_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'event_not_found');
    END IF;

    -- Hosts may not RSVP their own event as a guest.
    IF EXISTS (
        SELECT 1 FROM public.event_host
        WHERE  event_id = p_event_id AND person_id = p_person_id
    ) THEN
        RETURN jsonb_build_object('error', 'host_cannot_rsvp');
    END IF;

    -- Capacity check only applies when accepting.
    IF p_status = 'Accepted' AND v_event.max_capacity IS NOT NULL THEN
        SELECT COUNT(*) INTO v_accepted_count
        FROM   public.event_participation
        WHERE  event_id = p_event_id AND status = 'Accepted';

        IF v_accepted_count >= v_event.max_capacity THEN
            RETURN jsonb_build_object('error', 'event_full');
        END IF;
    END IF;

    -- Upsert: insert new or update existing RSVP status.
    INSERT INTO public.event_participation (person_id, event_id, status)
    VALUES (p_person_id, p_event_id, p_status)
    ON CONFLICT (person_id, event_id)
    DO UPDATE SET status = EXCLUDED.status;

    RETURN jsonb_build_object('success', true, 'status', p_status::text);
END;
$$;

GRANT EXECUTE ON FUNCTION public.rsvp_to_event(UUID, UUID, public.invitation_status_enum)
    TO authenticated;
