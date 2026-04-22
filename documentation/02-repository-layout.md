# Repository-Struktur

## Wurzelverzeichnis

| Pfad | Zweck |
|------|--------|
| `app/` | Python-Paket der Anwendung (FastAPI, Router, Core) |
| `tests/` | Testpaket (Platzhalter; Ausbau offen) |
| `documentation/` | Maintainer-Dokumentation (Markdown, nur im Repo) |
| `requirements.txt` | Python-Abhängigkeiten |
| `.env.example` | Vorlage für lokale Umgebungsvariablen (ohne Geheimnisse) |
| `Dockerfile` | Produktionsnahes Image (Multi-Stage) |
| `.dockerignore` | Reduziert den Build-Kontext (u. a. keine Doku im Image) |
| `.gitlab-ci.yml` | Pipeline: Build Registry-Image, optionales Deploy |
| `README.md` | Kurzüberblick, Setup, Verweise |

Hinweis: `IMPLEMENTATION.md` im Repo-Wurzelverzeichnis ist eine **kurze Bestandsaufnahme**; die ausführlichere, gepflegte Doku liegt unter `documentation/`.

## Paket `app/`

| Pfad | Zweck |
|------|--------|
| `main.py` | FastAPI-Instanz, CORS, Root- und Health-Routen, Einbindung von `api/v1` |
| `core/config.py` | `Settings` aus Umgebungsvariablen |
| `core/supabase.py` | Supabase-Client (URL + Anon Key) |
| `core/auth.py` | FastAPI-Dependencies: `get_current_user`, `get_current_user_optional` |
| `api/v1/router.py` | Sammelrouter unter Präfix `/api/v1` |
| `api/v1/*.py` | Feature-Router (z. B. `user.py`) |
| `schemas/` | Pydantic-Modelle für Request/Response |
| `services/` | Vorgesehen für fachliche Logik, DB-Zugriffe, externe APIs |
| `utils/` | Vorgesehen für kleine Hilfsfunktionen |

## Konventionen

- **API-Versionierung:** Neue öffentliche Routen unter `app/api/v1/` und Einbindung in `router.py`.
- **Geschützte Routen:** FastAPI-`Depends(get_current_user)` verwenden (siehe [04-authentication.md](04-authentication.md)).
- **Validierung:** Request-/Response-Modelle in `app/schemas/` kapseln.

## Neuen Endpoint hinzufügen (Checkliste)

1. Modul unter `app/api/v1/<feature>.py` mit `APIRouter` anlegen.
2. In `app/api/v1/router.py` importieren und mit `include_router(..., prefix="/<feature>", tags=[...])` einhängen.
3. Bei Bedarf Schemas in `app/schemas/` ergänzen.
4. In [05-http-api.md](05-http-api.md) (diese Doku) die Route kurz dokumentieren.
