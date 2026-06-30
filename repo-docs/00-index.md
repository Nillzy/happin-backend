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
| [15-user-account-api.md](15-user-account-api.md) | User-Account-API: Stats, eigene Events, Tickets, Name-Update, Konto-Löschung, Timestamp-Konvention |
| [16-infinity-scroll-pagination.md](16-infinity-scroll-pagination.md) | Infinity Scroll Backend-Fix: Total-Count statt Page-Count, Tuple-Return, Separate Count-Query |
| [17-ticket-system.md](17-ticket-system.md) | Ticket-System: Automatische Generierung bei RSVP, QR-Token, DB-Schema, Endpoints (M8) |
| [18-calendar-export.md](17-calendar-export.md) | Kalenderexport (ICS): Endpoint, iCalendar-Format, Frontend-Integration |
| [19-google-wallet.md](18-google-wallet.md) | Google Wallet: Event-Tickets als digitale Karten, JWT-Generierung, Service Account Setup |
| [19-events-filter.md](19-events-filter.md) | Events API filter parameters: date range, category, city, is_free |
| [20-event-absagen.md](20-event-absagen.md) | Event Absagen: `cancelled_at`-Feld, Cancel-Endpoint, Auto-Refund, Aktions-Sperren |
| [21-erinnerungen-k4.md](21-erinnerungen-k4.md) | Erinnerungen (K4): Tabellen, REST-Endpoints, APScheduler + pywebpush, VAPID-Setup |
| [22-rsvp-export.md](22-rsvp-export.md) | Gästelisten-Export (S8): CSV + PDF, Host-only, Filter accepted, eine Zeile pro Ticket |
| [23-weather-forecast.md](23-weather-forecast.md) | Wettervorhersage (S3): WeatherAPI.com-Integration, Host-Toggle, Graceful Degradation, On-Demand-Fetch |
| [24-documentation-concept.md](24-documentation-concept.md) | Dokumentationskonzept: Drei Dokus (`repo-docs/`, `docs/` via MkDocs unter `/docs`, Swagger unter `/api/docs`), Zielgruppen, Konventionen |
| [25-traceability.md](25-traceability.md) | Traceability-Konzept: Rückreferenzen Code → Architekturentwurf → Pflichtenheft → Lastenheft, Mx/Sx/Kx-IDs, URL-Fragment-Anchor-Pattern |

## Neue Dokumentation hinzufügen

1. Neue Datei unter `repo-docs/` anlegen, mit nummeriertem Präfix (z. B. `08-…`).
2. In dieser Tabelle eine Zeile mit Kurzbeschreibung und relativem Link ergänzen.

So bleibt die Sammlung **auffindbar** und die empfohlene Lesereihenfolge erkennbar.
