-- Add gradient_id column to event table for persisting gradient cover selection
ALTER TABLE public.event
  ADD COLUMN gradient_id smallint DEFAULT NULL;
