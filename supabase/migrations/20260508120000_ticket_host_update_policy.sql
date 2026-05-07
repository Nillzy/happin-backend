-- Hosts können Tickets ihres Events updaten (status auf 'used' setzen beim Scannen)
CREATE POLICY "Hosts can update event tickets" ON ticket
    FOR UPDATE USING (event_id IN (
        SELECT eh.event_id FROM event_host eh
        JOIN person p ON p.person_id = eh.person_id
        WHERE p.supabase_user_id = auth.uid()
    ));
