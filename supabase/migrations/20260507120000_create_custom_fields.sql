-- ============================================================
-- Migration: Benutzerdefinierte Formularfelder (Custom Fields)
-- ============================================================

-- ─── 1. Enum für Feldtypen ───────────────────────────────────────────────────

CREATE TYPE public.custom_field_type AS ENUM (
    'text',
    'textarea',
    'single_select',
    'multi_select'
);

-- ─── 2. Felddefinitionen pro Event ──────────────────────────────────────────

CREATE TABLE public.custom_field (
    custom_field_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        UUID NOT NULL REFERENCES public.event(event_id) ON DELETE CASCADE,
    label           TEXT NOT NULL,
    field_type      public.custom_field_type NOT NULL,
    is_required     BOOLEAN NOT NULL DEFAULT false,
    options         JSONB,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_custom_field_event ON public.custom_field(event_id);

ALTER TABLE public.custom_field ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anyone_select_custom_fields" ON public.custom_field
    FOR SELECT USING (true);

CREATE POLICY "host_insert_custom_fields" ON public.custom_field
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.event_host eh
            JOIN public.person p ON p.person_id = eh.person_id
            WHERE eh.event_id = custom_field.event_id
              AND p.supabase_user_id = auth.uid()
        )
    );

CREATE POLICY "host_update_custom_fields" ON public.custom_field
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.event_host eh
            JOIN public.person p ON p.person_id = eh.person_id
            WHERE eh.event_id = custom_field.event_id
              AND p.supabase_user_id = auth.uid()
        )
    );

CREATE POLICY "host_delete_custom_fields" ON public.custom_field
    FOR DELETE TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.event_host eh
            JOIN public.person p ON p.person_id = eh.person_id
            WHERE eh.event_id = custom_field.event_id
              AND p.supabase_user_id = auth.uid()
        )
    );

-- ─── 3. Gast-Antworten (Composite-PK) ──────────────────────────────────────

CREATE TABLE public.custom_field_response (
    event_participation_id UUID NOT NULL REFERENCES public.event_participation(event_participation_id) ON DELETE CASCADE,
    custom_field_id        UUID NOT NULL REFERENCES public.custom_field(custom_field_id) ON DELETE CASCADE,
    value                  JSONB NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (event_participation_id, custom_field_id)
);

CREATE INDEX idx_custom_field_response_field ON public.custom_field_response(custom_field_id);

ALTER TABLE public.custom_field_response ENABLE ROW LEVEL SECURITY;

CREATE POLICY "participant_insert_response" ON public.custom_field_response
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.event_participation ep
            JOIN public.person p ON p.person_id = ep.person_id
            WHERE ep.event_participation_id = custom_field_response.event_participation_id
              AND p.supabase_user_id = auth.uid()
        )
    );

CREATE POLICY "participant_update_response" ON public.custom_field_response
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.event_participation ep
            JOIN public.person p ON p.person_id = ep.person_id
            WHERE ep.event_participation_id = custom_field_response.event_participation_id
              AND p.supabase_user_id = auth.uid()
        )
    );

CREATE POLICY "select_own_or_host_response" ON public.custom_field_response
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.event_participation ep
            JOIN public.person p ON p.person_id = ep.person_id
            WHERE ep.event_participation_id = custom_field_response.event_participation_id
              AND p.supabase_user_id = auth.uid()
        )
        OR
        EXISTS (
            SELECT 1 FROM public.event_participation ep
            JOIN public.event_host eh ON eh.event_id = ep.event_id
            JOIN public.person p ON p.person_id = eh.person_id
            WHERE ep.event_participation_id = custom_field_response.event_participation_id
              AND p.supabase_user_id = auth.uid()
        )
    );
