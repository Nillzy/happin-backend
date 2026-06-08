# Happin — Docker-Abgabe

Lauffaehige Container-Abgabe des Happin-Projekts (Backend + Frontend).

## Inhalt des Bundles

Diese Datei (`happin-abgabe-<version>.tar.gz`) enthaelt nach dem Entpacken einen Ordner mit:

| Datei | Zweck |
|---|---|
| `docker-compose.yml` | Orchestriert beide Container |
| `backend.env` | Konfiguration Backend (Supabase, Stripe-Test-Mode, etc.) |
| `frontend.env` | Konfiguration Frontend |
| `happin-images.tar.gz` | Beide Docker-Images (Backend + Frontend) |
| `README.md` | Diese Anleitung |

## Voraussetzungen

- Docker Deamon
- Ports: **8001** (Backend) und **8080** (Frontend)

## Start

```bash
# 1. Bundle aus dem GitLab Release herunterladen
#    Release-Seite: https://gitlab.com/dhbw-se/se-tinf24b2/happin/backend/-/releases
#    Asset: "happin-abgabe-<version>.tar.gz"

# 2. Bundle entpacken und in den Ordner wechseln
tar -xzf happin-abgabe-*.tar.gz
cd happin-abgabe-*

# 3. Images in Dockers internen Speicher laden
docker load -i happin-images.tar.gz

# 4. Container starten
docker compose up -d

# 5. Status pruefen
docker compose ps
```

## Aufrufen

- **Frontend (Web):** http://localhost:8080
- **Backend Health-Check:** http://localhost:8001/health
- **Backend API-Docs (Swagger):** http://localhost:8001/docs

## Logs ansehen

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

## Stoppen

```bash
docker compose down
```

## Hinweise

- Die `.env`-Dateien enthalten **Test-Credentials** (Stripe Test-Mode, Test-Supabase-Instanz). Keine echten Zahlungen, keine Produktivdaten.
- Das Frontend-Image hat seine API-URL zur Build-Zeit ins Bundle kompiliert. Wenn das Frontend kein Backend findet, ist das vermutlich der Grund — Backend-Health-Check unter `/health` zeigt, ob das Backend selbst laeuft.
- Google-Wallet-Integration ist im Abgabe-Setup deaktiviert (Service-Account-Datei nicht enthalten).
