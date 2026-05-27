-- NULL = unbegrenzt viele Tickets pro Teilnehmer; 1 war der alte Default.
ALTER TABLE public.event
    ALTER COLUMN max_tickets_per_person DROP DEFAULT;

ALTER TABLE public.event
    ALTER COLUMN max_tickets_per_person SET DEFAULT NULL;
