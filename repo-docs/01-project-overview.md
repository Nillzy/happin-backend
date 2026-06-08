# Projektüberblick

## Was das ist

**Happin Backend** ist die HTTP-API der Happin-Plattform zur **Event-Discovery**. Sie ist in **Python** mit **FastAPI** implementiert und soll primär mit **Supabase** (PostgreSQL, Auth, ggf. Storage/Realtime) zusammenarbeiten.

Die Anwendung ist ein **ASGI**-Dienst; lokal und im Container startet sie typischerweise mit **Uvicorn**.

## Rolle im System

- **Auth (empfohlen):** Clients authentifizieren sich direkt gegen **Supabase Auth** (z. B. OTP). Das Backend erhält nur das **JWT** im `Authorization`-Header und **validiert** es über die Supabase-Client-API.
- **API:** Geschäftslogik und aggregierte Endpoints leben hier; persistente Daten liegen in Supabase/Postgres, nicht im App-Container.

## Tech-Stack (kurz)

| Bereich | Technologie |
|---------|-------------|
| Framework | FastAPI |
| Laufzeit | Python 3.11+ |
| Server | Uvicorn |
| Konfiguration | Pydantic Settings (`pydantic-settings`) |
| Backend-as-a-Service | Supabase Python Client |

## Project Structure

```
happin-backend/
├── app/                          # Application package
│   ├── main.py                   # FastAPI app instance, CORS, health routes, lifespan
│   ├── core/
│   │   ├── config.py             # Pydantic Settings — all env vars loaded here
│   │   ├── supabase.py           # Global Supabase client (lazy initialized)
│   │   └── auth.py               # JWT validation dependencies (get_current_user)
│   ├── api/
│   │   └── v1/
│   │       ├── router.py         # Aggregates all v1 sub-routers
│   │       ├── user.py           # /api/v1/user/* endpoints
│   │       ├── events.py         # /api/v1/events/* endpoints
│   │       └── ticket_options.py # /api/v1/events/{id}/ticket-options
│   ├── schemas/
│   │   ├── user.py               # UserResponse (Pydantic)
│   │   ├── events.py             # EventCreate, EventDetailResponse, EventListResponse
│   │   ├── participants.py       # RSVP participant schemas
│   │   └── ticket_options.py     # Ticket option schemas
│   ├── services/                 # Business logic and DB access
│   └── utils/                    # Helper functions (formatters, validators)
│
├── supabase/
│   ├── config.toml               # Supabase CLI project config
│   └── migrations/               # SQL migrations (timestamped)
│
├── tests/
│   ├── conftest.py               # Pytest fixtures; mocks Supabase before app import
│   ├── test_health.py            # Tests for /, /health, /api/v1/health
│   └── test_auth.py              # Tests for /api/v1/user/me auth flow
│
├── documentation/                # Technical documentation (you are here)
├── .env.example                  # Environment variables template (no secrets)
├── requirements.txt              # Python dependencies (pinned)
├── Dockerfile                    # Multi-stage build (builder + production)
├── .dockerignore
├── .gitlab-ci.yml                # CI/CD pipeline: test → build → deploy
└── README.md
```

**Key Modules:**

| Module | Responsibility |
|--------|----------------|
| `app/core/config.py` | Single source of truth for all environment variables |
| `app/core/auth.py` | JWT validation via Supabase; `get_current_user` dependency |
| `app/api/v1/router.py` | Registers all feature routers; add new endpoints here |
| `app/schemas/` | All request/response models — never inline in route files |
| `app/services/` | DB queries, external API calls, business rules |

## Status

The repository implements the MVP feature set: Auth validation, Event CRUD (Create, Read, Update), RSVP management, ticket options, and host overview. Tests run in CI, Docker images are automatically built and can be manually deployed.

See the following chapters and [README](../README.md) for details on structure and operations.
