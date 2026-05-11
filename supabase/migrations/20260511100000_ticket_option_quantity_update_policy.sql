-- Erlaubt authentifizierten Usern das Dekrementieren von quantity_limit beim Ticketkauf.
-- Die Autorisierungsprüfung (User eingeloggt, Event existiert) erfolgt im Backend.
CREATE POLICY "authenticated_decrement_ticket_option_quantity" ON public.ticket_option
  FOR UPDATE TO authenticated
  USING (true)
  WITH CHECK (true);
