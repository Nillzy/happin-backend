-- Kapazitätsprüfung: Tickets zählen statt Participations
-- 1 Ticket = 1 Person die reinkommt

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
    v_event        RECORD;
    v_ticket_count INTEGER;
BEGIN
    SELECT * INTO v_event
    FROM   public.event
    WHERE  event_id = p_event_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'event_not_found');
    END IF;

    -- Capacity check based on ticket count (1 ticket = 1 attendee)
    IF p_status = 'Accepted' AND v_event.max_capacity IS NOT NULL THEN
        SELECT COUNT(*) INTO v_ticket_count
        FROM   public.ticket
        WHERE  event_id = p_event_id;

        IF v_ticket_count >= v_event.max_capacity THEN
            RETURN jsonb_build_object('error', 'event_full');
        END IF;
    END IF;

    INSERT INTO public.event_participation (person_id, event_id, status)
    VALUES (p_person_id, p_event_id, p_status)
    ON CONFLICT (person_id, event_id)
    DO UPDATE SET status = EXCLUDED.status;

    RETURN jsonb_build_object('success', true, 'status', p_status::text);
END;
$$;
