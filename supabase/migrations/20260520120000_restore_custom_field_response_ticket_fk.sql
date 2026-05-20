-- FK custom_field_response.ticket_id -> ticket(ticket_id) wiederherstellen.
-- Hintergrund: 20260507120001 wurde nachträglich auf "DROP TABLE ... CASCADE" geändert.
-- Das CASCADE hat alle FKs gedroppt, die auf ticket(ticket_id) zeigten — u.a.
-- custom_field_response_ticket_id_fkey. Ohne diesen FK kann PostgREST die
-- Beziehung nicht auflösen ("Could not find a relationship between 'ticket'
-- and 'custom_field_response'", PGRST200) und GET /participants liefert 500.

-- 1) Verwaiste Responses entfernen, deren ticket_id nicht mehr existiert.
--    Sonst schlägt der FK-Add wegen 23503 fehl.
DELETE FROM public.custom_field_response cfr
WHERE cfr.ticket_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM public.ticket t WHERE t.ticket_id = cfr.ticket_id
  );

-- 2) FK wiederherstellen (idempotent)
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

-- 3) PostgREST Schema-Cache reloaden
NOTIFY pgrst, 'reload schema';
