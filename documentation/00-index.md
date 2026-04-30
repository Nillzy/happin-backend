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
| [09-event-creation.md](09-event-creation.md) | Event-Erstellung: DB-Migration, Person-Service, Erstellungs-Flow, POST-Endpoint, Validierung |
| [10-schema-optimization.md](10-schema-optimization.md) | Schema-Optimierung: participation-Merge, event_media PK, timestamptz, starts_at/ends_at, RLS-Policies |
| [11-event-draft-status.md](11-event-draft-status.md) | Event Draft-Status: DB-Migration, Access Control für Entwürfe, Veröffentlichungs-Flow, Sicherheitsmodell |
| [12-ticket-options.md](12-ticket-options.md) | Ticket-Optionen: Preiskategorien, ticket_option-Tabelle, RLS, UPSERT-Endpoint, is_free-Logik |
| [13-participant-management.md](13-participant-management.md) | Participant-Management: Host-Endpoints für Teilnehmer-Übersicht und -Verwaltung (M7) |
| [14-rsvp-and-event-host.md](14-rsvp-and-event-host.md) | RSVP-Funktion & event_host-Refactoring: DB-Migration, RSVP-Endpoint, RPC, is_host/my_rsvp_status (M5) |

## Neue Dokumentation hinzufügen

1. Neue Datei unter `documentation/` anlegen, mit nummeriertem Präfix (z. B. `08-…`).
2. In dieser Tabelle eine Zeile mit Kurzbeschreibung und relativem Link ergänzen.

So bleibt die Sammlung **auffindbar** und die empfohlene Lesereihenfolge erkennbar.
