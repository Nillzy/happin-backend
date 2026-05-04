# HTTP-API

## Basis-URLs

Lokal typischerweise `http://localhost:8001` (siehe README / Uvicorn-Port).

## Öffentliche Endpoints (ohne Bearer-Token)

| Methode | Pfad | Zweck |
|---------|------|--------|
| GET | `/` | Kurzinfo (Name, Version, Verweise auf Docs/Health) |
| GET | `/health` | Health für Loadbalancer/Monitoring |
| GET | `/api/v1/health` | Health innerhalb der Version **v1** |

## Geschützte Endpoints

| Methode | Pfad | Auth | Zweck |
|---------|------|------|--------|
| GET | `/api/v1/user/me` | Bearer JWT | Gibt Daten des angemeldeten Nutzers zurück (Beispiel/Profil-Test); Response-Schema: `UserResponse` |
| GET | `/api/v1/users/me/stats` | Bearer JWT | Statistiken des Nutzers (Events besucht/erstellt, Tickets, Teilnehmer) |
| GET | `/api/v1/users/me/events` | Bearer JWT | Eigene Events (Organizer + Teilnehmer); Query-Params: `period`, `role`, `limit`, `offset`; Details: [15-user-account-api.md](15-user-account-api.md) |
| GET | `/api/v1/users/me/tickets` | Bearer JWT | Eigene Tickets (Participations als Proxy); Details: [15-user-account-api.md](15-user-account-api.md) |
| PATCH | `/api/v1/users/me/name` | Bearer JWT | Vor- und Nachname in `person`-Tabelle aktualisieren |
| DELETE | `/api/v1/users/me` | Bearer JWT | Konto und alle Daten dauerhaft löschen; Details: [15-user-account-api.md](15-user-account-api.md) |
| POST | `/api/v1/events/` | Bearer JWT | Neues Event erstellen; Request-Schema: `EventCreate`, Response-Schema: `EventDetailResponse` (201); Details: [09-event-creation.md](09-event-creation.md) |
| POST | `/api/v1/events/{event_id}/rsvp` | Bearer JWT | RSVP erstellen oder ändern; Request-Schema: `RsvpRequest`, Response-Schema: `RsvpResponse`; Details: [14-rsvp-and-event-host.md](14-rsvp-and-event-host.md) |
| GET | `/api/v1/events/{event_id}/participants` | Bearer JWT (Host-only) | Teilnehmer-Liste mit Counts; Response-Schema: `ParticipantListResponse`; Details: [13-participant-management.md](13-participant-management.md) |
| DELETE | `/api/v1/events/{event_id}/participants` | Bearer JWT (Host-only) | Teilnehmer entfernen (Bulk); Request-Schema: `RemoveParticipantsRequest`; Details: [13-participant-management.md](13-participant-management.md) |

## Öffentliche Endpoints mit optionaler Auth

| Methode | Pfad | Auth | Zweck |
|---------|------|------|--------|
| GET | `/api/v1/events/` | Optional Bearer JWT | Öffentliche Events chronologisch auflisten; Query-Params: `limit` (1–100, default 50), `offset` (≥ 0, default 0); Response enthält `is_host: boolean` wenn Token mitgesendet; Response-Schema: `EventListResponse` |
| GET | `/api/v1/events/{event_id}` | Optional Bearer JWT | Einzelnes Event mit vollem Detail (Location, Media, Host); Response-Schema: `EventDetailResponse`; enthält `is_host` und `my_rsvp_status` wenn Token mitgesendet; 404 wenn nicht gefunden oder privates Event ohne Token |

Details zu den Event-Endpoints, Architektur-Entscheidungen und Supabase-Query-Mustern: siehe [08-events-api.md](08-events-api.md).

## OpenAPI / Swagger

Bei **`DEBUG=true`** stehen **`/docs`** (Swagger UI) und **`/redoc`** zur Verfügung. In Produktion sollte `DEBUG` aus bleiben, damit die interaktive Doku nicht öffentlich exponiert ist.

## CORS

In `app/main.py` ist aktuell **`allow_origins=["*"]`** gesetzt (mit TODO für produktive Einschränkung). Vor Go-Live bewusst auf erlaubte Origins reduzieren.

## Versionierung

Alle stabilen API-Routen sollten unter **`/api/v1/...`** liegen. Ein späteres `v2` wäre als zusätzlicher Router denkbar, ohne `v1` sofort zu brechen.
