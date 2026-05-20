-- 1) Stellt sicher, dass mehrere Tickets pro Person pro Event möglich sind.
--    Notwendig, weil 20260507120001 die Tabelle inkl. UNIQUE(event_id, person_id) neu erstellt
--    und 20260508100000 in diesem Fall nicht erneut läuft.
ALTER TABLE public.ticket DROP CONSTRAINT IF EXISTS ticket_event_id_person_id_key;

-- 2) FK custom_field_response.ticket_id -> ticket(ticket_id) wiederherstellen.
--    20260507120001 mit DROP TABLE ... CASCADE hat den FK mitgekippt; PostgREST kann
--    die Beziehung sonst nicht auflösen ("Could not find a relationship between
--    'ticket' and 'custom_field_response'").
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.custom_field_response'::regclass
          AND contype = 'f'
          AND confrelid = 'public.ticket'::regclass
    ) THEN
        ALTER TABLE public.custom_field_response
            ADD CONSTRAINT custom_field_response_ticket_id_fkey
            FOREIGN KEY (ticket_id) REFERENCES public.ticket(ticket_id) ON DELETE CASCADE;
    END IF;
END $$;

-- 3) PostgREST Schema-Cache reloaden, damit die neuen Beziehungen sofort greifen
NOTIFY pgrst, 'reload schema';
