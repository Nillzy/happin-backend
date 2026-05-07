-- Mehrere Tickets pro Person pro Event erlauben
ALTER TABLE public.ticket DROP CONSTRAINT ticket_event_id_person_id_key;
