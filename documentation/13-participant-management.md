# Participant Management (M7)

## Übersicht

Die Participant-Management-API ermöglicht Event-Hosts, Teilnehmer ihres Events einzusehen und zu verwalten. Die Endpoints sind nur für den jeweiligen Host zugänglich.

**Anforderung:** M7 (Host-Übersicht) aus dem Pflichtenheft

## Endpoints

### GET `/api/v1/events/{event_id}/participants`

Gibt alle Teilnehmer eines Events zurück, inklusive aggregierter Counts.

| Eigenschaft | Wert |
|-------------|------|
| Auth | Bearer JWT (required) |
| Berechtigung | Nur Event-Host |
| Response | `ParticipantListResponse` |
| Fehler | 401 (kein Token), 403 (kein Host), 404 (Event nicht gefunden) |

**Response-Beispiel:**

```json
{
  "participants": [
    {
      "participation_id": 42,
      "person": {
        "person_id": 1,
        "first_name": "Max",
        "last_name": "Mustermann",
        "phone_number": "+491234567890"
      },
      "status": "Accepted",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "counts": {
    "accepted": 5,
    "declined": 2,
    "pending": 3
  }
}
```

### DELETE `/api/v1/events/{event_id}/participants`

Entfernt Teilnehmer aus einem Event (Bulk-Operation). Hosts können nicht entfernt werden.

| Eigenschaft | Wert |
|-------------|------|
| Auth | Bearer JWT (required) |
| Berechtigung | Nur Event-Host |
| Request | `RemoveParticipantsRequest` |
| Response | `RemoveParticipantsResponse` |
| Fehler | 401 (kein Token), 403 (kein Host), 404 (Event nicht gefunden) |

**Request-Body:**

```json
{
  "participation_ids": [42, 43, 44]
}
```

**Response:**

```json
{
  "removed_count": 3
}
```

## Erweiterung: `is_host` Flag in Event-Liste

Der `GET /api/v1/events/` Endpoint wurde erweitert: Wenn ein Bearer-Token mitgesendet wird, enthält die Response für jedes Event ein `is_host: boolean` Feld. Damit kann das Frontend Events kennzeichnen, bei denen der User Host ist.

## Schemas

Definiert in `app/schemas/participants.py`:

| Schema | Zweck |
|--------|-------|
| `PersonInfo` | Basis-Personendaten (id, name, phone) |
| `ParticipantResponse` | Einzelner Teilnehmer mit Person, Status, Timestamp |
| `ParticipantCounts` | Aggregierte Counts (accepted, declined, pending) |
| `ParticipantListResponse` | Response für GET participants |
| `RemoveParticipantsRequest` | Request für DELETE participants |
| `RemoveParticipantsResponse` | Response für DELETE participants |

## Service-Funktionen

In `app/services/event_service.py`:

| Funktion | Zweck |
|----------|-------|
| `is_user_host(event_id, person_id)` | Prüft ob Person Host des Events ist |
| `get_event_participants(event_id)` | Lädt alle Teilnehmer mit Counts |
| `remove_participants(event_id, participation_ids, token)` | Entfernt Teilnehmer (keine Hosts) |

## Sicherheit

- **Host-only Access:** Beide Endpoints prüfen, ob der anfragende User Host des Events ist
- **Host-Schutz:** Hosts können nicht über den DELETE-Endpoint entfernt werden (Supabase-Query mit `.neq("role", "Host")`)
- **Event-Existenz:** Beide Endpoints prüfen zuerst, ob das Event existiert (404), bevor die Host-Berechtigung geprüft wird (403)

## Dateien

| Datei | Zweck |
|-------|-------|
| `app/schemas/participants.py` | Pydantic-Schemas |
| `app/services/event_service.py` | Service-Logik |
| `app/api/v1/events.py` | API-Endpoints |
| `tests/test_participants.py` | Unit- und Integrationstests |
