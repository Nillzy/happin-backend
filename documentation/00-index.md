# Dokumentation — Index

Diese Datei ist der **Einstiegspunkt** für Maintainer-Dokumentation. Sie ist **nicht** in die FastAPI-App eingebunden; die Markdown-Dateien werden im Editor oder in GitLab gelesen.

## Kapitelübersicht

| Datei | Inhalt |
|--------|--------|
| [01-project-overview.md](01-project-overview.md) | Was das Backend ist, Rolle im Gesamtsystem, Tech-Stack |
| [02-repository-layout.md](02-repository-layout.md) | Verzeichnisstruktur, Konventionen, wo neue Features hingehören |
| [03-configuration-and-secrets.md](03-configuration-and-secrets.md) | Umgebungsvariablen, `Settings`, `.env` / `.env.example` |
| [04-authentication.md](04-authentication.md) | JWT mit Supabase, `get_current_user`, empfohlener Frontend-Flow |
| [05-http-api.md](05-http-api.md) | Öffentliche und geschützte Endpoints, API-Versionierung |
| [06-local-development-and-docker.md](06-local-development-and-docker.md) | Lokales Setup, Uvicorn, Docker-Image |
| [07-ci-cd-and-deployment.md](07-ci-cd-and-deployment.md) | GitLab CI, Registry, manuelles Deploy |
| [08-events-api.md](08-events-api.md) | Events-API: Endpoints, Architektur-Entscheidungen, Supabase-Query-Muster, Schema-Mapping |

## Neue Dokumentation hinzufügen

1. Neue Datei unter `documentation/` anlegen, mit nummeriertem Präfix (z. B. `08-…`).
2. In dieser Tabelle eine Zeile mit Kurzbeschreibung und relativem Link ergänzen.

So bleibt die Sammlung **auffindbar** und die empfohlene Lesereihenfolge erkennbar.
