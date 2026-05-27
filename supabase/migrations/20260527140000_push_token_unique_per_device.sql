-- ============================================================
-- Migration: Push-Token/Subscription pro Gerät unique
--
-- Vorher: UNIQUE (person_id, token) bzw. (person_id, endpoint).
-- Damit konnte ein physisches Gerät zwei Personen gehören und der
-- Service hat über `user_agent` deduplizieren müssen — was bei
-- "ios 17.0"-Strings für mehrere iPhones derselben Person zu
-- gegenseitigem Löschen führte und beim User-Wechsel im selben
-- Browser zu Cross-User-Push-Leaks.
--
-- Nachher: token bzw. endpoint sind global unique. Beim Login auf
-- einem Gerät wird `person_id` per Upsert (on_conflict=token/endpoint)
-- übertragen. Genau eine Zeile pro Gerät, kein Geräte-Klau zwischen
-- Personen mehr möglich.
-- ============================================================

-- ─── expo_push_token ─────────────────────────────────────────────
-- Karteileichen aufräumen: pro Token nur die jüngste Zeile behalten.
DELETE FROM public.expo_push_token a
USING public.expo_push_token b
WHERE a.token = b.token
  AND a.expo_push_token_id <> b.expo_push_token_id
  AND a.updated_at < b.updated_at;

ALTER TABLE public.expo_push_token
    DROP CONSTRAINT IF EXISTS expo_push_token_person_id_token_key;

ALTER TABLE public.expo_push_token
    ADD CONSTRAINT expo_push_token_token_key UNIQUE (token);

-- ─── web_push_subscription ───────────────────────────────────────
-- Tabelle hat kein updated_at — über created_at deduplizieren.
DELETE FROM public.web_push_subscription a
USING public.web_push_subscription b
WHERE a.endpoint = b.endpoint
  AND a.web_push_subscription_id <> b.web_push_subscription_id
  AND a.created_at < b.created_at;

ALTER TABLE public.web_push_subscription
    DROP CONSTRAINT IF EXISTS web_push_subscription_person_id_endpoint_key;

ALTER TABLE public.web_push_subscription
    ADD CONSTRAINT web_push_subscription_endpoint_key UNIQUE (endpoint);
