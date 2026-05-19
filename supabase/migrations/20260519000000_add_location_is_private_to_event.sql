-- Add location_is_private flag to event table
ALTER TABLE public.event
  ADD COLUMN location_is_private BOOLEAN NOT NULL DEFAULT FALSE;