# Erinnerungen (K4) — Backend

Backend-Anteil der Anforderung **K4**: Web-Push-Versand für Reminder, sowie
REST-Endpoints für Settings + Subscription-Verwaltung.

## Tabellen

Migration: `supabase/migrations/20260521150000_add_reminder_feature.sql`

| Tabelle | Zweck | RLS |
|---------|-------|-----|
| `reminder_preference` | `enabled`, `lead_time_minutes` (1..10080) pro Person | „own preferences" |
| `web_push_subscription` | `endpoint`, `p256dh_key`, `auth_key` pro Browser/Gerät | „own subscriptions" |
| `reminder_sent` | Idempotenz: `(event_id, person_id)` | nur Service-Role |

## REST-Endpoints

Alle unter `/api/v1/users/...`, JWT erforderlich (außer VAPID-Public-Key).

| Methode | Pfad | Beschreibung |
|--------|------|---------------|
| `GET`  | `/me/reminder-preferences` | Aktuelle Präferenzen (Defaults wenn leer) |
| `PATCH`| `/me/reminder-preferences` | Upsert von `enabled` und/oder `lead_time_minutes` |
| `POST` | `/me/web-push-subscriptions` | Subscription registrieren (`endpoint`, `keys.p256dh`, `keys.auth`) |
| `DELETE`| `/me/web-push-subscriptions` | Subscription per `endpoint` entfernen |
| `GET`  | `/vapid-public-key` | Public-Key für `pushManager.subscribe` |

## Scheduler

Modul: `app/services/reminder_scheduler.py`

`AsyncIOScheduler` startet im FastAPI-Lifespan mit `IntervalTrigger(seconds=60)`
(siehe `REMINDER_SCHEDULER_INTERVAL_SECONDS`). Pro Tick:

1. Alle `reminder_preference` mit `enabled=true` lesen.
2. Pro Person: `event_participation` (Status `Accepted`) joinen.
3. Events filtern: `deleted_at IS NULL` und `starts_at - lead_time` im Fenster
   `[now, now+intervall]`.
4. Bereits gesendete Events (`reminder_sent`) ausschließen.
5. Web-Push-Subscriptions der Person laden.
6. `pywebpush.webpush(...)` mit VAPID-Claims senden.
7. Bei Erfolg: `INSERT INTO reminder_sent`.
8. Bei `404`/`410`: Subscription löschen.

Der Scheduler ist No-Op solange `VAPID_PRIVATE_KEY` fehlt — der Server startet
auch ohne Web-Push-Konfiguration.

## VAPID-Keys generieren

```bash
python -c "from py_vapid import Vapid01; v=Vapid01(); v.generate_keys(); \
  print('priv:', v.private_pem().decode()); print('pub:', v.public_key)"
```

In `.env`:
```
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_SUBJECT=mailto:admin@happin.fun
REMINDER_SCHEDULER_ENABLED=true
REMINDER_SCHEDULER_INTERVAL_SECONDS=60
```

## Manuelles Testen

```bash
TOKEN=...
curl -X PATCH localhost:8001/api/v1/users/me/reminder-preferences \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"enabled":true,"lead_time_minutes":120}'

curl localhost:8001/api/v1/users/me/reminder-preferences \
  -H "Authorization: Bearer $TOKEN"
```

## Architekturhinweis (Native vs. Web)

Native-Erinnerungen werden vom Frontend via `expo-notifications` lokal auf dem
Gerät gescheduled — das Backend ist daran nicht beteiligt. Diese Tabellen und
der Scheduler dienen ausschließlich dem **Web-Push-Pfad**.
