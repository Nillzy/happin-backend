-- Alte ticket-Tabelle durch neues QR-basiertes Schema ersetzen (M8)
-- Die alte Tabelle (PK ticket_number, FK event_participation_id) wird nicht produktiv genutzt.

DROP INDEX IF EXISTS idx_ticket_participation;
DROP POLICY IF EXISTS "Users can read own tickets" ON ticket;
DROP POLICY IF EXISTS "Hosts can read event tickets" ON ticket;
DROP POLICY IF EXISTS "Service role full access" ON ticket;
DROP TABLE IF EXISTS public.ticket;

CREATE TABLE public.ticket (
    ticket_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES event(event_id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    ticket_option_id UUID REFERENCES ticket_option(ticket_option_id),
    qr_token TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'used', 'expired')),
    created_at TIMESTAMPTZ DEFAULT now(),
    used_at TIMESTAMPTZ,
    UNIQUE(event_id, person_id)
);

CREATE INDEX idx_ticket_qr_token ON ticket(qr_token);

ALTER TABLE ticket ENABLE ROW LEVEL SECURITY;

-- User kann eigene Tickets lesen
CREATE POLICY "Users can read own tickets" ON ticket
    FOR SELECT USING (person_id IN (
        SELECT person_id FROM person WHERE supabase_user_id = auth.uid()
    ));

-- User kann eigene Tickets erstellen
CREATE POLICY "Users can insert own tickets" ON ticket
    FOR INSERT WITH CHECK (person_id IN (
        SELECT person_id FROM person WHERE supabase_user_id = auth.uid()
    ));

-- User kann eigene Tickets löschen
CREATE POLICY "Users can delete own tickets" ON ticket
    FOR DELETE USING (person_id IN (
        SELECT person_id FROM person WHERE supabase_user_id = auth.uid()
    ));

-- Host kann Tickets seines Events lesen (für späteres Scanning)
CREATE POLICY "Hosts can read event tickets" ON ticket
    FOR SELECT USING (event_id IN (
        SELECT eh.event_id FROM event_host eh
        JOIN person p ON p.person_id = eh.person_id
        WHERE p.supabase_user_id = auth.uid()
    ));
