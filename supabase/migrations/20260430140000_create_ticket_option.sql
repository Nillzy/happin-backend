-- ============================================================
-- Migration: Ticket-Optionen (Preiskategorien pro Event)
-- ============================================================

-- Explizite Entscheidung: Event kostenlos oder kostenpflichtig
ALTER TABLE public.event ADD COLUMN is_free boolean NOT NULL DEFAULT true;

-- Ticket-Optionen (Preiskategorien)
CREATE TABLE public.ticket_option (
    ticket_option_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id uuid NOT NULL REFERENCES public.event(event_id) ON DELETE CASCADE,
    name text NOT NULL,
    description text,
    price numeric(10,2) NOT NULL DEFAULT 0.00,
    quantity_limit integer,
    sort_order integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_ticket_option_event ON public.ticket_option(event_id);

ALTER TABLE public.ticket_option ENABLE ROW LEVEL SECURITY;

-- Jeder darf Ticket-Optionen lesen (Sichtbarkeit über Event-Zugriff gesteuert)
CREATE POLICY "anyone_select_ticket_options" ON public.ticket_option
  FOR SELECT USING (true);

-- Nur Host darf Optionen erstellen
CREATE POLICY "host_insert_ticket_options" ON public.ticket_option
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.event_participation ep
      JOIN public.person p ON p.person_id = ep.person_id
      WHERE ep.event_id = ticket_option.event_id
        AND ep.role = 'Host'
        AND p.supabase_user_id = auth.uid()
    )
  );

-- Nur Host darf Optionen bearbeiten
CREATE POLICY "host_update_ticket_options" ON public.ticket_option
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.event_participation ep
      JOIN public.person p ON p.person_id = ep.person_id
      WHERE ep.event_id = ticket_option.event_id
        AND ep.role = 'Host'
        AND p.supabase_user_id = auth.uid()
    )
  );

-- Nur Host darf Optionen löschen
CREATE POLICY "host_delete_ticket_options" ON public.ticket_option
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.event_participation ep
      JOIN public.person p ON p.person_id = ep.person_id
      WHERE ep.event_id = ticket_option.event_id
        AND ep.role = 'Host'
        AND p.supabase_user_id = auth.uid()
    )
  );
