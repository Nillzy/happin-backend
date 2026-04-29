-- =============================================================================
-- Migration: Convert all integer primary keys to UUID
-- =============================================================================
-- Strategy: Drop constraints, TRUNCATE all data, alter column types, recreate constraints.
-- gen_random_uuid() is built into PostgreSQL 13+ (Supabase default).
-- =============================================================================

-- ─── 1. Drop ALL foreign key constraints ────────────────────────────────────

ALTER TABLE public.ticket
  DROP CONSTRAINT IF EXISTS ticket_event_participation_id_fkey;

ALTER TABLE public.event_media
  DROP CONSTRAINT IF EXISTS event_media_event_id_fkey;

ALTER TABLE public.event_media
  DROP CONSTRAINT IF EXISTS event_media_uploader_id_fkey;

ALTER TABLE public.event_participation
  DROP CONSTRAINT IF EXISTS event_participation_event_id_fkey;

ALTER TABLE public.event_participation
  DROP CONSTRAINT IF EXISTS event_participation_person_id_fkey;

ALTER TABLE public.event
  DROP CONSTRAINT IF EXISTS event_location_id_fkey;

-- ─── 2. Drop unique constraints that reference PK columns ───────────────────

ALTER TABLE public.event_participation
  DROP CONSTRAINT IF EXISTS unique_person_event;

-- ─── 3. Drop primary key constraints ────────────────────────────────────────

ALTER TABLE public.event_media DROP CONSTRAINT IF EXISTS event_media_pkey;
ALTER TABLE public.event_participation DROP CONSTRAINT IF EXISTS event_participation_pkey;
ALTER TABLE public.event DROP CONSTRAINT IF EXISTS event_pkey;
ALTER TABLE public.location DROP CONSTRAINT IF EXISTS location_pkey;
ALTER TABLE public.person DROP CONSTRAINT IF EXISTS person_pkey;

-- ─── 4. Drop indexes on columns that will change type ───────────────────────

DROP INDEX IF EXISTS public.idx_event_location;
DROP INDEX IF EXISTS public.idx_event_participation_event;
DROP INDEX IF EXISTS public.idx_event_participation_person;
DROP INDEX IF EXISTS public.idx_ticket_participation;

-- ─── 5. TRUNCATE all tables ─────────────────────────────────────────────────

TRUNCATE public.ticket,
         public.event_media,
         public.event_participation,
         public.event,
         public.location,
         public.person
CASCADE;

-- ─── 6. ALTER columns: PK columns from integer → uuid ───────────────────────

-- Drop identity (must be separate from type change)
ALTER TABLE public.person ALTER COLUMN person_id DROP IDENTITY IF EXISTS;
ALTER TABLE public.location ALTER COLUMN location_id DROP IDENTITY IF EXISTS;
ALTER TABLE public.event ALTER COLUMN event_id DROP IDENTITY IF EXISTS;
ALTER TABLE public.event_participation ALTER COLUMN event_participation_id DROP IDENTITY IF EXISTS;
ALTER TABLE public.event_media ALTER COLUMN media_id DROP IDENTITY IF EXISTS;

-- Change PK column types to uuid
ALTER TABLE public.person
  ALTER COLUMN person_id SET DATA TYPE uuid USING gen_random_uuid(),
  ALTER COLUMN person_id SET DEFAULT gen_random_uuid();

ALTER TABLE public.location
  ALTER COLUMN location_id SET DATA TYPE uuid USING gen_random_uuid(),
  ALTER COLUMN location_id SET DEFAULT gen_random_uuid();

ALTER TABLE public.event
  ALTER COLUMN event_id SET DATA TYPE uuid USING gen_random_uuid(),
  ALTER COLUMN event_id SET DEFAULT gen_random_uuid();

ALTER TABLE public.event
  ALTER COLUMN location_id SET DATA TYPE uuid USING gen_random_uuid();

ALTER TABLE public.event_participation
  ALTER COLUMN event_participation_id SET DATA TYPE uuid USING gen_random_uuid(),
  ALTER COLUMN event_participation_id SET DEFAULT gen_random_uuid();

ALTER TABLE public.event_participation
  ALTER COLUMN person_id SET DATA TYPE uuid USING gen_random_uuid();

ALTER TABLE public.event_participation
  ALTER COLUMN event_id SET DATA TYPE uuid USING gen_random_uuid();

ALTER TABLE public.event_media
  ALTER COLUMN media_id SET DATA TYPE uuid USING gen_random_uuid(),
  ALTER COLUMN media_id SET DEFAULT gen_random_uuid();

ALTER TABLE public.event_media
  ALTER COLUMN uploader_id SET DATA TYPE uuid USING gen_random_uuid();

ALTER TABLE public.event_media
  ALTER COLUMN event_id SET DATA TYPE uuid USING gen_random_uuid();

-- ticket (FK column only, PK stays varchar)
ALTER TABLE public.ticket
  ALTER COLUMN event_participation_id SET DATA TYPE uuid USING gen_random_uuid();

-- ─── 7. Re-add primary keys ─────────────────────────────────────────────────

ALTER TABLE public.person ADD PRIMARY KEY (person_id);
ALTER TABLE public.location ADD PRIMARY KEY (location_id);
ALTER TABLE public.event ADD PRIMARY KEY (event_id);
ALTER TABLE public.event_participation ADD PRIMARY KEY (event_participation_id);
ALTER TABLE public.event_media ADD PRIMARY KEY (media_id);

-- ─── 8. Re-add foreign key constraints (all ON DELETE CASCADE) ──────────────

ALTER TABLE public.event
  ADD CONSTRAINT event_location_id_fkey
  FOREIGN KEY (location_id) REFERENCES public.location(location_id) ON DELETE CASCADE;

ALTER TABLE public.event_participation
  ADD CONSTRAINT event_participation_person_id_fkey
  FOREIGN KEY (person_id) REFERENCES public.person(person_id) ON DELETE CASCADE;

ALTER TABLE public.event_participation
  ADD CONSTRAINT event_participation_event_id_fkey
  FOREIGN KEY (event_id) REFERENCES public.event(event_id) ON DELETE CASCADE;

ALTER TABLE public.event_media
  ADD CONSTRAINT event_media_event_id_fkey
  FOREIGN KEY (event_id) REFERENCES public.event(event_id) ON DELETE CASCADE;

ALTER TABLE public.event_media
  ADD CONSTRAINT event_media_uploader_id_fkey
  FOREIGN KEY (uploader_id) REFERENCES public.person(person_id) ON DELETE CASCADE;

ALTER TABLE public.ticket
  ADD CONSTRAINT ticket_event_participation_id_fkey
  FOREIGN KEY (event_participation_id) REFERENCES public.event_participation(event_participation_id) ON DELETE CASCADE;

-- ─── 9. Re-add unique constraints and indexes ───────────────────────────────

ALTER TABLE public.event_participation
  ADD CONSTRAINT unique_person_event UNIQUE (person_id, event_id);

CREATE INDEX idx_event_location ON public.event USING btree (location_id);
CREATE INDEX idx_event_participation_event ON public.event_participation USING btree (event_id);
CREATE INDEX idx_event_participation_person ON public.event_participation USING btree (person_id);
CREATE INDEX idx_ticket_participation ON public.ticket USING btree (event_participation_id);

-- ─── 10. Drop orphaned sequences ────────────────────────────────────────────

DROP SEQUENCE IF EXISTS public.event_event_id_seq;
DROP SEQUENCE IF EXISTS public.event_participation_event_participation_id_seq;
DROP SEQUENCE IF EXISTS public.location_location_id_seq;
DROP SEQUENCE IF EXISTS public.person_person_id_seq;
DROP SEQUENCE IF EXISTS public.event_media_media_id_seq;
