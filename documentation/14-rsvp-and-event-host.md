# RSVP-Funktion & event_host-Refactoring (M5)

## Übersicht

Dieses Dokument beschreibt die RSVP-Funktion für Gäste sowie das DB-Refactoring, das Hosts aus `event_participation` in eine eigene `event_host`-Tabelle ausgelagert hat.

**Anforderung:** M5 (RSVP) aus dem Pflichtenheft

---

## DB-Migration: `event_host`-Tabelle

**Migration:** `supabase/migrations/20260501000000_add_event_host_and_rsvp_rpc.sql`

### Motivation

Vorher wurden Hosts und Gäste in `event_participation` gemischt (über `role = 'Host'` vs. `role = 'Participant'`). Das führte zu:
- Komplizierter UPSERT-Logik (Host-Einträge durften nicht überschrieben werden)
- Unklarer `participant_count`-Semantik (zählte auch Hosts)
- Schwierigem Host-Check (immer WHERE `role = 'Host'` nötig)

### Neue Struktur

```sql
CREATE TABLE public.event_host (
  event_host_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  event_id      UUID NOT NULL REFERENCES public.event(event_id) ON DELETE CASCADE,
  person_id     UUID NOT NULL REFERENCES public.person(person_id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(event_id, person_id)
);
```

Alle bestehenden Host-Einträge wurden migriert, die `role`-Spalte aus `event_participation` entfernt:

```sql
INSERT INTO public.event_host (event_id, person_id, created_at)
SELECT event_id, person_id, created_at
FROM public.event_participation WHERE role = 'Host';

DELETE FROM public.event_participation WHERE role = 'Host';
ALTER TABLE public.event_participation DROP COLUMN role;
```

`event_participation` enthält damit **ausschließlich Gast-RSVPs** (kein `role`-Feld mehr).

### RLS für `event_host`

| Policy | Rolle | Zugriff |
|--------|-------|---------|
| `select_event_host` | anon, authenticated | SELECT (alle) |
| `insert_event_host` | authenticated | INSERT |

---

## RSVP-Endpoint

### `POST /api/v1/events/{event_id}/rsvp`

| Eigenschaft | Wert |
|-------------|------|
| Auth | Bearer JWT (required) |
| Request | `RsvpRequest` |
| Response | `RsvpResponse` |
| Fehler | 400, 401, 404, 409 |

**Request-Body:**

```json
{ "status": "Accepted" }
```

Erlaubte Status-Werte: `Accepted`, `Declined`, `Pending`

**Response:**

```json
{
  "event_participation_id": "d4e5f6a7-...",
  "event_id": "a1b2c3d4-...",
  "person_id": "e5f6a7b8-...",
  "status": "Accepted"
}
```

**Fehler-Codes:**

| Code | Grund |
|------|-------|
| 400 | Event bereits gestartet (`event_in_past`) |
| 400 | Öffentliches Event erlaubt nur `Accepted` (`public_event_accepted_only`) |
| 400 | Host kann nicht am eigenen Event RSVP'en (`host_cannot_rsvp`) |
| 404 | Event nicht gefunden |
| 409 | Event ausgebucht (`event_full`) |

### RSVP-Regeln

- **Öffentliche Events:** Nur `Accepted` möglich (kein `Pending`, kein `Declined` direkt — Declined entfernt den Status implizit)
- **Private Events:** Alle drei Status erlaubt (`Accepted`, `Declined`, `Pending`)
- **Änderung:** Jederzeit möglich, solange `starts_at > NOW()`
- **Eindeutigkeit:** Ein RSVP pro Account (DB-`UNIQUE(person_id, event_id)`)

### RPC `rsvp_to_event`

Das eigentliche UPSERT läuft über eine PostgreSQL-Funktion, die Race Conditions beim letzten freien Platz verhindert:

```sql
SELECT * FROM public.event FOR UPDATE;  -- Reihen-Lock
```

Die RPC prüft:
1. Event existiert
2. User ist kein Host
3. Kapazität nicht überschritten (nur bei `Accepted`)
4. UPSERT in `event_participation`

Der Service-Layer in `rsvp_event()` prüft zusätzlich vor dem RPC-Call: Zeitpunkt (`event_in_past`) und öffentliches Event + Status.

---

## Neue Felder in `EventDetailResponse`

### `my_rsvp_status`

Wenn ein Bearer-Token mitgesendet wird, enthält die Detail-Response den aktuellen RSVP-Status des eingeloggten Users:

```json
{ "my_rsvp_status": "Accepted" }
```

`null` wenn kein Token oder kein RSVP vorhanden.

### `is_host`

Sowohl `EventListItem` als auch `EventDetailResponse` enthalten jetzt `is_host: boolean`. Wird `true` wenn der eingeloggte User Host des Events ist.

Beide Felder werden im Service-Layer (`get_event_by_id`) berechnet, nicht in `_to_detail`.

---

## Private Events: Sichtbarkeit

### Problem

Die Supabase-RLS-Policy erlaubt dem Anon-Key nur `is_public = true` zu lesen:

```sql
CREATE POLICY "anon_select_public_events" ON public.event
  FOR SELECT TO anon USING (is_public = true);

CREATE POLICY "auth_select_events" ON public.event
  FOR SELECT TO authenticated USING (true);
```

### Lösung

`get_event_by_id` akzeptiert einen optionalen `token`-Parameter. Wenn ein Token vorhanden ist, wird `get_supabase_for_user(token)` verwendet (authentifizierter Client), der die `auth_select_events`-Policy nutzt und private Events sieht.

```python
supabase = get_supabase_for_user(token) if token else get_supabase()
```

Der `GET /api/v1/events/{event_id}`-Endpoint extrahiert den Token über `optional_bearer` und gibt ihn weiter. Ohne Token sind private Events nicht erreichbar (404).

---

## Service-Funktionen (Übersicht)

In `app/services/event_service.py`:

| Funktion | Signatur | Zweck |
|----------|----------|-------|
| `get_event_by_id` | `(event_id, supabase_user_id?, token?)` | Event laden; setzt `is_host` + `my_rsvp_status` im Dict |
| `rsvp_event` | `(event_id, supabase_user_id, email, status, token)` | RSVP erstellen oder aktualisieren |
| `create_event` | `(data, person_id, token, supabase_user_id?)` | Event + Host-Eintrag anlegen |
| `update_event` | `(event_id, data, person_id, token, supabase_user_id?)` | Event aktualisieren (nur Host) |

---

## Schema-Mapping (aktualisiert)

| API-Feld | Quelle | Anmerkung |
|----------|--------|-----------|
| `host_name` | `event_host[0].person.first_name + last_name` | Eigene Tabelle, kein `role`-Filter mehr |
| `participant_count` | `len(event_participation)` | Nur noch Gäste, keine Hosts mehr |
| `is_host` | `event_host` WHERE `supabase_user_id` matches | Berechnet in `get_event_by_id` |
| `my_rsvp_status` | `event_participation` WHERE `supabase_user_id` matches | `null` wenn kein Token oder kein RSVP |

---

## Dateien

| Datei | Zweck |
|-------|-------|
| `supabase/migrations/20260501000000_add_event_host_and_rsvp_rpc.sql` | DB-Migration: `event_host`-Tabelle, `role`-Spalte entfernen, RPC |
| `app/schemas/events.py` | `RsvpRequest`, `RsvpResponse`, `my_rsvp_status`, `is_host` |
| `app/services/event_service.py` | `rsvp_event`, angepasste `get_event_by_id`, `create_event`, `update_event` |
| `app/api/v1/events.py` | `POST /{event_id}/rsvp`, aktualisierter `GET /{event_id}` |
| `tests/test_events.py` | Tests auf neue `event_host`-Struktur angepasst |
