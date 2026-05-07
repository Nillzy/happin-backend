-- INSERT/DELETE-Policies für ticket-Tabelle hinzufügen
-- Damit User eigene Tickets über RLS erstellen/löschen können (ohne Service-Key)

DROP POLICY IF EXISTS "Service role full access" ON ticket;

CREATE POLICY "Users can insert own tickets" ON ticket
    FOR INSERT WITH CHECK (person_id IN (
        SELECT person_id FROM person WHERE supabase_user_id = auth.uid()
    ));

CREATE POLICY "Users can delete own tickets" ON ticket
    FOR DELETE USING (person_id IN (
        SELECT person_id FROM person WHERE supabase_user_id = auth.uid()
    ));
