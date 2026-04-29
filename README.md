# Happin Backend

REST-API der **Happin Event-Discovery-Plattform**, gebaut mit FastAPI und Python 3.11+. Der Dienst übernimmt Geschäftslogik, Datenzugriff auf Supabase/PostgreSQL und JWT-Validierung — die Authentifizierung selbst wird an Supabase Auth delegiert.

---

## Inhaltsverzeichnis

1. [Tech-Stack](#tech-stack)
2. [Systemarchitektur](#systemarchitektur)
3. [Verzeichnisstruktur](#verzeichnisstruktur)
4. [Voraussetzungen](#voraussetzungen)
5. [Lokales Setup](#lokales-setup)
6. [Umgebungsvariablen](#umgebungsvariablen)
7. [API-Endpunkte](#api-endpunkte)
8. [Tests](#tests)
9. [Docker](#docker)
10. [CI/CD](#cicd)
11. [Weiterentwicklung](#weiterentwicklung)
12. [Maintainer-Dokumentation](#maintainer-dokumentation)

---

## Tech-Stack

| Bereich | Technologie | Version |
|---------|-------------|---------|
| Sprache | Python | 3.11+ |
| Framework | FastAPI | 0.109.0 |
| ASGI-Server | Uvicorn | 0.27.0 |
| Datenvalidierung | Pydantic / pydantic-settings | v2 |
| Datenbank & Auth | Supabase (PostgreSQL + Auth) | 2.10.0 |
| Tests | pytest + pytest-asyncio + httpx | 7.4 / 0.21 / 0.27 |
| Container | Docker (Multi-Stage) | — |
| CI/CD | GitLab CI | — |

---

## Systemarchitektur

```
┌─────────────────────────────────────────────────────────┐
│                        Clients                          │
│          (Expo Mobile App / Browser)                    │
└────────────────┬──────────────────┬─────────────────────┘
                 │                  │
      ① OTP-Login direkt       ② JWT bei jedem
        an Supabase Auth          API-Request
                 │                  │
                 ▼                  ▼
┌────────────────────┐   ┌────────────────────────────────┐
│   Supabase Auth    │   │       Happin Backend           │
│  (Phone OTP, JWT)  │   │    FastAPI  ·  Port 8001       │
└────────────────────┘   │                                │
          │              │  ┌──────────────────────────┐  │
          │ JWT          │  │  app/core/auth.py        │  │
          └─────────────►│  │  supabase.auth.get_user  │  │
                         │  └──────────────────────────┘  │
                         │                                │
                         │  ┌──────────────────────────┐  │
                         │  │  app/api/v1/             │  │
                         │  │  Router → Services       │  │
                         │  └──────────────────────────┘  │
                         └───────────────┬────────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  Supabase (Postgres) │
                              │  Projekt: HappinDB   │
                              └──────────────────────┘
```

**Ablauf:**

1. Die App authentifiziert sich direkt bei **Supabase Auth** (Phone OTP) und erhält ein JWT.
2. Alle geschützten API-Aufrufe senden `Authorization: Bearer <jwt>`.
3. Das Backend validiert das JWT über den Supabase-Client (`supabase.auth.get_user(token)`) — kein eigenes Schlüsselmaterial nötig.
4. Business-Logik und Datenbankzugriffe erfolgen ausschließlich über den **Supabase Python Client**.

---

## Verzeichnisstruktur

```
backend/
├── app/                        # Anwendungspaket
│   ├── main.py                 # FastAPI-Instanz, CORS, Health-Routen, Lifespan-Hooks
│   ├── core/
│   │   ├── config.py           # Pydantic Settings — lädt alle Env-Variablen typsicher
│   │   ├── supabase.py         # Globaler Supabase-Client (lazy initialisiert)
│   │   └── auth.py             # FastAPI-Dependencies: get_current_user / get_current_user_optional
│   ├── api/
│   │   └── v1/
│   │       ├── router.py       # Aggregiert alle v1-Sub-Router
│   │       ├── user.py         # /api/v1/user/* Endpoints
│   │       └── events.py       # /api/v1/events/* Endpoints
│   ├── schemas/
│   │   ├── user.py             # UserResponse (Pydantic)
│   │   └── event.py            # EventCreate, EventDetailResponse, EventListResponse
│   ├── services/               # Business-Logik und DB-Zugriffe
│   └── utils/                  # Hilfsfunktionen (pure functions, formatter, validator)
│
├── supabase/
│   ├── config.toml             # Supabase-CLI-Projektkonfiguration
│   └── migrations/             # Versionierte SQL-Migrations (Zeitstempel-Prefix)
│
├── tests/
│   ├── conftest.py             # Pytest-Fixtures; mockt Supabase vor App-Import
│   ├── test_health.py          # Tests für /, /health, /api/v1/health
│   └── test_auth.py            # Tests für /api/v1/user/me Auth-Flow
│
├── documentation/              # Ausführliche Maintainer-Doku (Markdown)
├── .env.example                # Vorlage für Umgebungsvariablen (ohne Secrets)
├── requirements.txt            # Python-Abhängigkeiten (pinned)
├── Dockerfile                  # Multi-Stage Build (Builder + Production)
├── .dockerignore
├── .gitlab-ci.yml              # Pipeline: test → build → deploy (manuell)
└── README.md
```

### Schlüsselmodule im Überblick

| Modul | Verantwortung |
|-------|---------------|
| `app/core/config.py` | Einzige Stelle, an der Env-Variablen definiert und eingelesen werden |
| `app/core/auth.py` | JWT-Validierung; `get_current_user` und optionale Variante für FastAPI `Depends()` |
| `app/api/v1/router.py` | Registriert alle Feature-Router; hier eintragen beim Hinzufügen neuer Endpoints |
| `app/schemas/` | Alle Request-/Response-Modelle — niemals inline in Route-Dateien |
| `app/services/` | DB-Queries, externe API-Calls, fachliche Regeln |

---

## Voraussetzungen

- **Python 3.11+** (`python --version`)
- **pip**
- Optional: **Docker** (für Container-Build und lokale Compose-Setups)
- Optional: **Supabase CLI** (für Datenbankmigrationen — Installationsanleitung unter `documentation/06-local-development-and-docker.md`)

---

## Lokales Setup

```bash
# 1. Repository klonen
git clone https://gitlab.com/dhbw-se/se-tinf24b2/happin/backend.git
cd backend

# 2. Virtuelle Umgebung anlegen und aktivieren
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Abhängigkeiten installieren
pip install -r requirements.txt

# 4. Umgebungsvariablen konfigurieren
cp .env.example .env
# .env mit eigenen Supabase-Keys befüllen (siehe Abschnitt Umgebungsvariablen)

# 5. Entwicklungsserver starten
uvicorn app.main:app --reload --port 8001
```

Nach dem Start erreichbar unter:

| URL | Zweck |
|-----|-------|
| `http://localhost:8001/` | API-Root (Name, Version, Links) |
| `http://localhost:8001/health` | Health-Check |
| `http://localhost:8001/docs` | Swagger UI (nur wenn `DEBUG=true`) |
| `http://localhost:8001/redoc` | ReDoc (nur wenn `DEBUG=true`) |

---

## Umgebungsvariablen

Vorlage liegt in `.env.example`. Die Datei `.env` wird **nicht** ins Git committed.

| Variable | Pflicht | Beschreibung |
|----------|---------|--------------|
| `SUPABASE_URL` | Ja | URL der Supabase-Instanz (lokal: `http://localhost:8000`) |
| `SUPABASE_ANON_KEY` | Ja | Öffentlicher Anon-Key des Supabase-Projekts |
| `SUPABASE_JWT_SECRET` | Ja | JWT-Secret für lokale Token-Validierung |
| `DATABASE_URL` | Nein | PostgreSQL-Connection-String (Supabase-Client wird bevorzugt) |
| `DEBUG` | Nein | `true` aktiviert Swagger UI und detaillierte Fehlermeldungen (Standard: `false`) |
| `LOG_LEVEL` | Nein | Log-Verbosity: `debug`, `info`, `warning`, `error` (Standard: `info`) |

Alle Variablen werden über `pydantic-settings` in `app/core/config.py` geladen. Fehlende Pflichtfelder führen beim Start zu einem Validierungsfehler.

---

## API-Endpunkte

Alle stabilen Routen liegen unter dem Präfix `/api/v1`.

### Öffentlich (kein Token erforderlich)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/` | API-Info (Name, Version, Links) |
| GET | `/health` | Health-Check für Load-Balancer / Monitoring |
| GET | `/api/v1/health` | Health-Check innerhalb der API-Version v1 |

### Öffentlich mit optionalem Token

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/v1/events/` | Events auflisten; Query-Params: `limit` (1–100), `offset` (≥ 0) |
| GET | `/api/v1/events/{event_id}` | Einzelnes Event mit vollem Detail; `404` wenn nicht gefunden |

### Geschützt (Bearer JWT erforderlich)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/v1/user/me` | Profil des angemeldeten Nutzers (`UserResponse`) |
| POST | `/api/v1/events/` | Neues Event erstellen (`EventCreate` → `EventDetailResponse`, Status 201) |

Vollständige Schnittstellenbeschreibung: `documentation/05-http-api.md`.

---

## Tests

```bash
# Alle Tests ausführen
pytest tests/ --tb=short

# CI-Modus (ohne Warnings)
pytest tests/ --tb=short -p no:warnings
```

Die Tests mocken den Supabase-Client **vor** dem App-Import. Dieses Muster darf nicht verändert werden:

```python
# tests/conftest.py
with patch("supabase.create_client", return_value=_mock_supabase):
    from app.main import app
```

Jeder Test erhält die Fixtures `client` (httpx `TestClient`) und `mock_supabase` (zurückgesetzter Mock). Mock-Rückgabewerte immer pro Test setzen, nicht global.

---

## Docker

### Image bauen und starten

```bash
# Image bauen
docker build -t happin-backend .

# Container starten
docker run -p 8001:8001 --env-file .env happin-backend
```

Das Image verwendet einen **Multi-Stage Build** (Builder + Production) und läuft als nicht-root-Nutzer `appuser`. Der eingebaute Health-Check ruft `GET /health` alle 30 Sekunden auf.

### Docker Compose (Monorepo)

```bash
cd ..   # Monorepo-Root
docker-compose up backend
```

---

## CI/CD

Die GitLab-Pipeline (`.gitlab-ci.yml`) durchläuft drei Stufen:

| Stage | Trigger | Beschreibung |
|-------|---------|--------------|
| `test` | Push auf `main` und Merge Requests | `pytest` ausführen |
| `build` | Push auf `main` | Docker-Image bauen und in die GitLab Container Registry pushen (Tags: Commit-SHA + `latest`) |
| `deploy` | Manuell in GitLab UI | Per SSH auf `vm552.ipp-vps.net` einloggen und `docker compose` aktualisieren |

**Erforderliche GitLab CI/CD-Variablen:**

| Variable | Zweck |
|----------|-------|
| `SSH_PRIVATE_KEY` | SSH-Key für das Deployment auf der VM |
| `GITLAB_DEPLOY_TOKEN` | Registry-Login auf der VM |
| `GITLAB_DEPLOY_USERNAME` | Registry-Benutzername |

**Produktions-URL:** `http://vm552.ipp-vps.net:8001`

---

## Weiterentwicklung

### Neuen Endpoint hinzufügen

1. Modul `app/api/v1/<feature>.py` mit `APIRouter` anlegen:

   ```python
   from fastapi import APIRouter, Depends
   from app.core.auth import get_current_user

   router = APIRouter()

   @router.get("/")
   async def list_feature(user = Depends(get_current_user)):
       return []
   ```

2. Router in `app/api/v1/router.py` registrieren:

   ```python
   from app.api.v1 import feature
   router.include_router(feature.router, prefix="/feature", tags=["feature"])
   ```

3. Schemas in `app/schemas/<feature>.py` ergänzen.
4. Endpoint in `documentation/05-http-api.md` dokumentieren.

### Datenbankmigrationen

Schemaänderungen werden über die **Supabase CLI** verwaltet:

```bash
# Schema vom Remote holen
supabase db pull

# Neue Migration lokal erstellen
supabase migration new <beschreibung>

# Lokale Migrations auf Remote anwenden
supabase db push
```

Supabase-Projekt: **HappinDB** · Project-Ref: `hylnqapjtkgqyxvmfqgy`

Migration-Dateien liegen unter `supabase/migrations/` und werden im Git versioniert. Ausführlichere Anleitung: `documentation/06-local-development-and-docker.md`.

---

## Weiterführende Dokumentation

Ausführliche technische und organisatorische Dokumentation liegt unter `documentation/` (Einstieg: `documentation/00-index.md`).

**Neue Themen, die in keine bestehende Datei passen, erhalten eine eigene Datei und einen Eintrag in `00-index.md`.**

*DHBW Karlsruhe — Software Engineering TINF24B2 — Happin*