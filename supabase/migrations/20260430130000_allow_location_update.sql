-- ============================================================
-- Migration: Tighten RLS policies for event and location updates
-- ============================================================
-- Only the host of an event may update the event or its location.
-- Uses auth.uid() to match against person.supabase_user_id via
-- the event_participation join (role = 'Host').
-- ============================================================

-- Replace the overly permissive event update policy
DROP POLICY IF EXISTS "auth_update_events" ON public.event;
CREATE POLICY "host_update_events" ON public.event
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.event_participation ep
      JOIN public.person p ON p.person_id = ep.person_id
      WHERE ep.event_id = event.event_id
        AND ep.role = 'Host'
        AND p.supabase_user_id = auth.uid()
    )
  );

-- Add location update policy (was missing entirely)
CREATE POLICY "host_update_locations" ON public.location
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.event e
      JOIN public.event_participation ep ON ep.event_id = e.event_id
      JOIN public.person p ON p.person_id = ep.person_id
      WHERE e.location_id = location.location_id
        AND ep.role = 'Host'
        AND p.supabase_user_id = auth.uid()
    )
  );
