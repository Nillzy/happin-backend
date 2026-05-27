-- ============================================================
-- Migration: Expo Push Tokens für native iOS/Android Apps
--
-- Wird parallel zu web_push_subscription verwendet — der Push-Fanout
-- bedient beide Tabellen. Tokens kommen aus Notifications.getExpoPushTokenAsync()
-- und haben das Format "ExponentPushToken[xxx]".
-- ============================================================

CREATE TABLE public.expo_push_token (
    expo_push_token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id          UUID NOT NULL REFERENCES public.person(person_id) ON DELETE CASCADE,
    token              TEXT NOT NULL,
    platform           TEXT NOT NULL CHECK (platform IN ('ios', 'android')),
    user_agent         TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (person_id, token)
);

CREATE INDEX idx_expo_push_token_person ON public.expo_push_token(person_id);

ALTER TABLE public.expo_push_token ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own_expo_push_token" ON public.expo_push_token
    FOR SELECT TO authenticated
    USING (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

CREATE POLICY "insert_own_expo_push_token" ON public.expo_push_token
    FOR INSERT TO authenticated
    WITH CHECK (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

CREATE POLICY "update_own_expo_push_token" ON public.expo_push_token
    FOR UPDATE TO authenticated
    USING (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

CREATE POLICY "delete_own_expo_push_token" ON public.expo_push_token
    FOR DELETE TO authenticated
    USING (
        person_id = (SELECT person_id FROM public.person WHERE supabase_user_id = auth.uid())
    );

GRANT SELECT, INSERT, UPDATE, DELETE ON public.expo_push_token TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.expo_push_token TO service_role;
