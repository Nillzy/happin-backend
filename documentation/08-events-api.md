# Events-API

Dieses Dokument beschreibt die Events-API, die Architektur-Entscheidungen dahinter, und wie das Muster für neue Endpoints übernommen werden kann.

## Endpoints

| Methode | Pfad | Auth | Zweck |
|---------|------|------|--------|
| GET | `/api/v1/events/` | Optional (Bearer JWT) | Öffentliche Events chronologisch auflisten |
| GET | `/api/v1/events/{event_id}` | Optional (Bearer JWT) | Einzelnes Event mit allen Details |

### `GET /api/v1/events/`

**Query-Parameter:**

| Parameter | Typ | Default | Bereich | Beschreibung |
|-----------|-----|---------|---------|-------------|
| `limit` | int | 50 | 1–100 | Maximale Anzahl Events pro Anfrage |
| `offset` | int | 0 | ≥ 0 | Offset für Pagination |

**Response:** `EventListResponse`

```json
{
  "events": [
    {
      "event_id": 1,
      "title": "Techno Night Berlin",
      "starts_at": "2026-05-10T22:00:00+00:00",
      "ends_at": null,
      "description": "...",
      "category": "Musik",
      "max_capacity": 500,
      "is_public": true,
      "image_url": "https://...",
      "location": {
        "location_id": 1,
        "city": "Berlin",
        "street": "Revaler Str.",
        "house_number": "99",
        "postal_code": "10245",
        "country": "Deutschland",
        "type": "Club"
      },
      "participant_count": 42
    }
  ],
  "count": 1
}
```

### `GET /api/v1/events/{event_id}`

**Response:** `EventDetailResponse` — erweitert `EventListItem` um:
- `invitation_link` — Einladungslink
- `created_at`, `updated_at` — Timestamps
- `host_name` — Name des Hosts (aus `event_host` → `person`)
- `media_urls` — Alle Media-URLs des Events

**Fehler:** `404` wenn Event nicht existiert.

## Architektur-Entscheidungen

### Auth: `get_current_user_optional`

Beide Endpoints nutzen `Depends(get_current_user_optional)` statt keiner Auth-Dependency. Das Browsen öffentlicher Events ist ohne Token möglich (Rückgabe `None`), aber das User-Objekt steht für zukünftige Personalisierung bereit (z.B. "Bereits zugesagt" anzeigen). Kein Breaking Change nötig wenn Auth-Features hinzukommen.

### Pagination: Limit/Offset statt Cursor

Für Sprint 1 reicht `limit`/`offset` — es mappt direkt auf Supabase `.range()` und ist einfach zu implementieren. Cursor-basierte Pagination (effizienter bei großen Datenmengen) kann in Sprint 3+ nachgerüstet werden, ohne das Frontend-Interface zu brechen (ein optionaler `cursor`-Parameter ist rückwärtskompatibel).

### Service-Layer

Business-Logik liegt in `app/services/event_service.py`, **nicht** inline in den Route-Handlern. Gründe:
- **Testbarkeit:** Tests können den Service mocken statt die gesamte Supabase-Kette
- **Wiederverwendung:** Andere Endpoints (z.B. zukünftige RSVP-Logik) können dieselben Service-Funktionen nutzen
- **Übersichtlichkeit:** Route-Handler bleiben schlank und fokussieren sich auf HTTP-Concerns (Validierung, Status-Codes)

## Supabase-Query-Muster (PostgREST Embedded Resources)

Die Supabase Python-Bibliothek nutzt PostgREST, das automatische Joins über Foreign-Key-Beziehungen unterstützt:

```python
supabase.table("event").select(
    "*, location(*), event_media(media_url), "
    "event_host(person(person_id, supabase_user_id, first_name, last_name)), "
    "event_participation(event_participation_id, status, person(person_id, supabase_user_id))"
)
```

- `location(*)` — Join über `event.location_id → location.location_id`, gibt alle Location-Spalten zurück
- `event_media(media_url)` — Reverse-Join über `event_media.event_id → event.event_id`, gibt nur `media_url` zurück
- `event_host(person(...))` — Reverse-Join über `event_host.event_id → event.event_id`, gibt Host-Person zurück
- `event_participation(..., person(...))` — Verschachtelte Joins: Participation (nur Gäste) → Person

**Wichtig:** Dieses Muster funktioniert nur, wenn die Foreign-Key-Constraints in der DB korrekt definiert sind. Die Migration `20260428140517_remote_schema.sql` definiert alle notwendigen Keys.

### Muster für neue Joins übernehmen

Wenn ein neuer Endpoint z.B. Tickets laden muss:

```python
supabase.table("ticket").select(
    "*, event_participation(*, event(*))"
)
```

Die verschachtelte Syntax folgt dem Foreign-Key-Pfad.

## Schema-Mapping: DB → API

| API-Feld | Quelle | Anmerkung |
|----------|--------|-----------|
| `image_url` | Erste URL aus `event_media` | Kein dediziertes `hero_image`-Feld in der DB |
| `participant_count` | `len(event_participation)` | Zählt nur Gäste (keine Hosts mehr) |
| `host_name` | `event_host[0].person.first_name + last_name` | Eigene Tabelle, kein `role`-Filter mehr |
| `is_host` | `event_host` WHERE `supabase_user_id` matches | Berechnet in `get_event_by_id`, `false` wenn kein Token |
| `my_rsvp_status` | `event_participation` WHERE `supabase_user_id` matches | `null` wenn kein Token oder kein RSVP |
| `media_urls` | Alle URLs aus `event_media` | Nur im Detail-Endpoint |

## Bekannte Schema-Lücken (Sprint 2+)

| Feature | Status | Workaround |
|---------|--------|-----------|
| Preis auf Event-Ebene | Preis nur auf `ticket`-Tabelle | Frontend zeigt "Preis auf Anfrage" |
| Lineup/Programm | Keine DB-Repräsentation | Abschnitt wird ausgeblendet wenn leer |
| Event-Titelbild | Kein dediziertes Feld | Erste URL aus `event_media` wird verwendet |

## Dateien

| Datei | Zweck |
|-------|-------|
| `app/schemas/events.py` | Pydantic Response-Modelle |
| `app/services/event_service.py` | Supabase-Queries (Business-Logik) |
| `app/api/v1/events.py` | FastAPI Router mit Endpoints |
| `tests/test_events.py` | Pytest-Tests |
