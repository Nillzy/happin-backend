# Happin Backend

FastAPI Backend für die Happin Event-Discovery Plattform.

---

## Setup

### Voraussetzungen

- Python 3.11 oder höher
- pip
- Optional für **Supabase CLI** (`login`, `link`, Migrationen): siehe **`documentation/06-local-development-and-docker.md`** (Installation und Einrichtung für das Team-Projekt)

### Installation

1. **Virtual Environment erstellen:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Mac/Linux
   # oder
   .venv\Scripts\activate  # Windows
   ```

2. **Dependencies installieren:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables konfigurieren:**
   ```bash
   cp .env.example .env
   # .env mit echten Supabase Keys befüllen
   ```
   
   **Wichtig:** `.env` wird NICHT ins Git committed!

4. **Server starten:**
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

5. **API Dokumentation öffnen:**
   - Swagger UI: http://localhost:8001/docs (nur im Debug-Modus)
   - Health Check: http://localhost:8001/health

---

## Tech Stack

- **Framework:** FastAPI
- **Python:** 3.11+
- **Server:** Uvicorn (ASGI)
- **Database:** Supabase (PostgreSQL + Auth + Storage + Realtime)
- **Validation:** Pydantic

---

## Maintainer-Dokumentation

Ausführliche, **reine Markdown**-Dokumentation für Maintainer liegt unter **`documentation/`** (Einstieg: `documentation/00-index.md`). Sie ist **nicht** in die Laufzeit-App eingebunden und dient Lesen im Editor oder auf GitLab. Details zu Aufbau und Pflege stehen im Index.

## Projektstruktur

```
backend/
├── app/
│   ├── core/                    # Kern-Konfiguration
│   │   ├── config.py            # Settings aus .env laden
│   │   ├── supabase.py          # Supabase Client
│   │   └── auth.py              # JWT Authentication Middleware
│   │
│   ├── api/v1/                  # API Endpoints
│   │   └── router.py            # Haupt-Router
│   │
│   ├── schemas/                 # Pydantic Models (Request/Response)
│   ├── services/                # Business Logic
│   ├── utils/                   # Helper Functions
│   └── main.py                  # FastAPI App Entry Point
│
├── documentation/               # Maintainer-Doku (Markdown, siehe 00-index.md)
├── tests/                       # Tests
├── .env.example                 # Environment Template
├── requirements.txt             # Dependencies
├── Dockerfile                   # Docker Setup
└── README.md
```

### Ordner-Übersicht

**`app/core/`** - Zentrale Konfiguration und Authentication
- Environment Variables laden mit Type Safety
- Datenbank-Client Setup
- JWT Authentication Middleware

**`app/api/v1/`** - HTTP Endpoints
- FastAPI Router mit Endpoints
- Request/Response Handling
- API Versioning

**`app/schemas/`** - Datenvalidierung
- Pydantic Models für API Input/Output
- Automatische Validierung durch FastAPI

**`app/services/`** - Business Logic
- Datenbank Queries
- Business Rules
- Externe API Calls

**`app/utils/`** - Hilfsfunktionen
- Pure Functions, Validatoren, Formatter

---

## Wichtige Implementierungs-Hinweise

### Authentication Flow (Option 1 - Empfohlen)

**Frontend ↔ Supabase direkt:**
1. Frontend sendet OTP-Anfrage an Supabase Auth
2. Supabase sendet SMS mit Code
3. Frontend verifiziert OTP bei Supabase → erhält JWT
4. Frontend sendet API-Requests mit JWT im Header
5. Backend validiert JWT bei jedem Request

**Vorteile:** Weniger Backend-Code, Supabase macht Auth automatisch

### Neue Endpoints hinzufügen

1. **Router erstellen** in `app/api/v1/`:
   ```python
   # app/api/v1/events.py
   from fastapi import APIRouter, Depends
   from app.core.auth import get_current_user
   
   router = APIRouter()
   
   @router.get("/")
   async def get_events(user = Depends(get_current_user)):
       return {"events": []}
   ```

2. **Router einbinden** in `app/api/v1/router.py`:
   ```python
   from app.api.v1 import events
   
   router.include_router(events.router, prefix="/events", tags=["events"])
   ```

### Protected Endpoints

```python
from app.core.auth import get_current_user

@router.post("/events")
async def create_event(user = Depends(get_current_user)):
    # user ist automatisch validiert und enthält Supabase User
    return {"creator_id": user.id}
```

### Environment Variables

**Debug-Modus aktivieren** (zeigt API Docs und detaillierte Errors):
```bash
# .env
DEBUG=true
```

**Production** (Docs disabled, sichere Error-Ausgaben):
```bash
DEBUG=false  # oder weglassen (default)
```

### Dependencies hinzufügen

Neue Bibliothek in `requirements.txt` eintragen:
```txt
stripe>=7.0.0
```

Dann installieren:
```bash
pip install -r requirements.txt
```

---

## Docker

### Build & Run

```bash
# Image bauen
docker build -t happin-backend .

# Container starten
docker run -p 8001:8001 --env-file .env happin-backend
```

### Mit Docker Compose (empfohlen)

```bash
cd ..  # Root-Verzeichnis
docker-compose up backend
```

---

## CI/CD

GitLab CI/CD Pipeline baut automatisch Docker Images bei Push zu `main`:

- **Build Stage:** Docker Image wird gebaut und zu GitLab Container Registry gepusht
- **Deploy Stage:** Manuelles Deployment zur VM (`when: manual`)

### GitLab Variables

In GitLab UI setzen:
- `SSH_PRIVATE_KEY` - SSH Key für VM Deployment
