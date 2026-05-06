-- Make uploader_id nullable on event_media so stock images (no uploader) can be stored
ALTER TABLE public.event_media
  ALTER COLUMN uploader_id DROP NOT NULL;
