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

## Zustand der Codebasis

Aktuell ist das Repository ein **funktionsfähiges Grundgerüst**: App-Shell, CORS, Health-Checks, Supabase-Client, JWT-Validierung und ein **Beispiel-Endpoint** für den angemeldeten Nutzer (`GET /api/v1/user/me`). Ordner wie `app/services/` und `app/utils/` sind vorgesehen, aber noch ohne fachliche Implementierung; Tests sind in CI vorbereitet, aber nicht aktiv geschaltet.

Weitere Details zu Struktur und Betrieb stehen in den folgenden Kapiteln und im [README](../README.md).
