-- Make location.city nullable
-- Location fields should be nullable when event is in draft status

ALTER TABLE public.location ALTER COLUMN city DROP NOT NULL;
