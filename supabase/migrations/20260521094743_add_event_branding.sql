-- Akzentfarben für Event-Branding (nullable, '#RRGGBB'-Format)
ALTER TABLE public.event
  ADD COLUMN accent_color_primary VARCHAR(7) DEFAULT NULL;

ALTER TABLE public.event
  ADD COLUMN accent_color_secondary VARCHAR(7) DEFAULT NULL;
