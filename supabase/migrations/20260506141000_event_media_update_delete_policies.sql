-- Add missing UPDATE and DELETE RLS policies to event_media
-- so event hosts can change or remove cover images after initial creation.

CREATE POLICY "update_media" ON public.event_media
  FOR UPDATE TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "delete_media" ON public.event_media
  FOR DELETE TO authenticated
  USING (true);
