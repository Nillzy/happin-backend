-- Create waitlist table and add waitlist_promotion_hours to event

CREATE TABLE public.event_waitlist (
  waitlist_id           uuid        NOT NULL DEFAULT gen_random_uuid(),
  event_id              uuid        NOT NULL,
  person_id             uuid        NOT NULL,
  joined_at             timestamptz NOT NULL DEFAULT now(),
  status                text        NOT NULL DEFAULT 'waiting'
                        CHECK (status IN ('waiting', 'notified', 'expired', 'removed')),
  notified_at           timestamptz,
  promotion_expires_at  timestamptz,
  CONSTRAINT event_waitlist_pkey    PRIMARY KEY (waitlist_id),
  CONSTRAINT event_waitlist_unique  UNIQUE (event_id, person_id),
  CONSTRAINT event_waitlist_event_fkey   FOREIGN KEY (event_id)   REFERENCES public.event(event_id),
  CONSTRAINT event_waitlist_person_fkey  FOREIGN KEY (person_id)  REFERENCES public.person(person_id)
);

ALTER TABLE public.event
  ADD COLUMN waitlist_promotion_hours integer NOT NULL DEFAULT 24;

-- RLS
ALTER TABLE public.event_waitlist ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own waitlist entries"
  ON public.event_waitlist FOR SELECT
  USING (person_id = (
    SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid()
  ));

CREATE POLICY "Users can join waitlist"
  ON public.event_waitlist FOR INSERT
  WITH CHECK (person_id = (
    SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid()
  ));

CREATE POLICY "Users can update own waitlist entry"
  ON public.event_waitlist FOR UPDATE
  USING (person_id = (
    SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid()
  ));

CREATE POLICY "Hosts can view event waitlist"
  ON public.event_waitlist FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM public.event_host eh
    WHERE eh.event_id = event_waitlist.event_id
      AND eh.person_id = (
        SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid()
      )
  ));
