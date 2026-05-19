-- Migration: Move custom_field_response from participation-level to ticket-level
-- Also adds max_tickets_per_person to event table

-- 1. New field on event table
ALTER TABLE public.event ADD COLUMN IF NOT EXISTS max_tickets_per_person INTEGER DEFAULT 1;

-- 2. Add ticket_id column to custom_field_response
ALTER TABLE public.custom_field_response
    ADD COLUMN IF NOT EXISTS ticket_id UUID REFERENCES public.ticket(ticket_id) ON DELETE CASCADE;

-- 3. Migrate existing data: assign responses to the first ticket of the same person+event
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'custom_field_response'
          AND column_name = 'event_participation_id'
    ) THEN
        UPDATE public.custom_field_response cfr
        SET ticket_id = (
            SELECT t.ticket_id FROM public.ticket t
            JOIN public.event_participation ep ON ep.person_id = t.person_id AND ep.event_id = t.event_id
            WHERE ep.event_participation_id = cfr.event_participation_id
            ORDER BY t.created_at ASC
            LIMIT 1
        );

        -- 4. Remove orphaned rows (no matching ticket found)
        DELETE FROM public.custom_field_response WHERE ticket_id IS NULL;
    END IF;
END $$;

-- 5. Drop existing RLS policies that depend on event_participation_id
DROP POLICY IF EXISTS "participant_insert_response" ON public.custom_field_response;
DROP POLICY IF EXISTS "participant_update_response" ON public.custom_field_response;
DROP POLICY IF EXISTS "select_own_or_host_response" ON public.custom_field_response;
DROP POLICY IF EXISTS "Guests can insert own responses" ON public.custom_field_response;
DROP POLICY IF EXISTS "Guests can update own responses" ON public.custom_field_response;
DROP POLICY IF EXISTS "Guests can read own responses" ON public.custom_field_response;
DROP POLICY IF EXISTS "Hosts can read event responses" ON public.custom_field_response;

-- 6. Drop old PK and FK, set new PK
DO $$
BEGIN
    -- Drop old PK if it still references event_participation_id
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'custom_field_response'
          AND column_name = 'event_participation_id'
    ) THEN
        ALTER TABLE public.custom_field_response DROP CONSTRAINT custom_field_response_pkey;
        ALTER TABLE public.custom_field_response DROP COLUMN event_participation_id;
    END IF;
END $$;
ALTER TABLE public.custom_field_response ALTER COLUMN ticket_id SET NOT NULL;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.custom_field_response'::regclass
          AND contype = 'p'
    ) THEN
        ALTER TABLE public.custom_field_response ADD PRIMARY KEY (ticket_id, custom_field_id);
    END IF;
END $$;

-- 7. Create new RLS policies based on ticket ownership
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='custom_field_response' AND policyname='Guests can insert own responses') THEN
        CREATE POLICY "Guests can insert own responses" ON public.custom_field_response
            FOR INSERT WITH CHECK (
                ticket_id IN (
                    SELECT ticket_id FROM public.ticket WHERE person_id IN (
                        SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid()
                    )
                )
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='custom_field_response' AND policyname='Guests can update own responses') THEN
        CREATE POLICY "Guests can update own responses" ON public.custom_field_response
            FOR UPDATE USING (
                ticket_id IN (
                    SELECT ticket_id FROM public.ticket WHERE person_id IN (
                        SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid()
                    )
                )
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='custom_field_response' AND policyname='Guests can read own responses') THEN
        CREATE POLICY "Guests can read own responses" ON public.custom_field_response
            FOR SELECT USING (
                ticket_id IN (
                    SELECT ticket_id FROM public.ticket WHERE person_id IN (
                        SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid()
                    )
                )
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='custom_field_response' AND policyname='Hosts can read event responses') THEN
        CREATE POLICY "Hosts can read event responses" ON public.custom_field_response
            FOR SELECT USING (
                ticket_id IN (
                    SELECT t.ticket_id FROM public.ticket t
                    JOIN public.event_host eh ON eh.event_id = t.event_id
                    JOIN public.person p ON p.person_id = eh.person_id
                    WHERE p.supabase_user_id = auth.uid()
                )
            );
    END IF;
END $$;
