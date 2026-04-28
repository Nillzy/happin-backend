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
| POST | `/api/v1/events/` | Bearer JWT | Neues Event erstellen; Request-Schema: `EventCreate`, Response-Schema: `EventDetailResponse` (201); Details: [09-event-creation.md](09-event-creation.md) |

## Öffentliche Endpoints mit optionaler Auth

| Methode | Pfad | Auth | Zweck |
|---------|------|------|--------|
| GET | `/api/v1/events/` | Optional Bearer JWT | Öffentliche Events chronologisch auflisten; Query-Params: `limit` (1–100, default 50), `offset` (≥ 0, default 0); Response-Schema: `EventListResponse` |
| GET | `/api/v1/events/{event_id}` | Optional Bearer JWT | Einzelnes Event mit vollem Detail (Location, Media, Host); Response-Schema: `EventDetailResponse`; 404 wenn nicht gefunden |

Details zu den Event-Endpoints, Architektur-Entscheidungen und Supabase-Query-Mustern: siehe [08-events-api.md](08-events-api.md).

## OpenAPI / Swagger

Bei **`DEBUG=true`** stehen **`/docs`** (Swagger UI) und **`/redoc`** zur Verfügung. In Produktion sollte `DEBUG` aus bleiben, damit die interaktive Doku nicht öffentlich exponiert ist.

## CORS

In `app/main.py` ist aktuell **`allow_origins=["*"]`** gesetzt (mit TODO für produktive Einschränkung). Vor Go-Live bewusst auf erlaubte Origins reduzieren.

## Versionierung

Alle stabilen API-Routen sollten unter **`/api/v1/...`** liegen. Ein späteres `v2` wäre als zusätzlicher Router denkbar, ohne `v1` sofort zu brechen.
