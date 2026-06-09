# Happin — Docker-Abgabe

Hier liegt alles, was man braucht, um Happin lokal als Docker-Setup zu starten — Backend und Frontend in zwei Containern, fertig konfiguriert.

## Inhalt des Bundles

Diese Datei (`happin-abgabe-<version>.tar.gz`) enthält nach dem Entpacken einen Ordner mit:

| Datei | Zweck |
|---|---|
| `docker-compose.yml` | Orchestriert beide Container |
| `backend.env` | Konfiguration Backend (Supabase, Stripe-Test-Mode, etc.) |
| `frontend.env` | Konfiguration Frontend |
| `happin-images.tar.gz` | Beide Docker-Images (Backend + Frontend) |
| `README.md` | Diese Anleitung |

## Voraussetzungen

- Docker Daemon (z. B. Docker Desktop, Colima, ...)
- Ports: **8001** (Backend) und **8080** (Frontend)

## Start

1. **Images herunterladen** von der [Release-Seite](https://gitlab.com/dhbw-se/se-tinf24b2/happin/backend/-/releases).

```bash
# Bundle entpacken und in den Ordner wechseln
tar -xzf happin-abgabe-*.tar.gz
cd happin-abgabe-*

# Images in Dockers internen Speicher laden
docker load -i happin-images.tar.gz

# Container starten
docker compose up -d

# Status prüfen
docker compose ps
```

## Aufrufen

- **Frontend (Web):** http://localhost:8080

## Stoppen

```bash
docker compose down
```

## Hinweise

- Die `.env`-Dateien enthalten **Test-Credentials** (Stripe Test-Mode, Test-Supabase-Instanz). Keine echten Zahlungen, keine Produktivdaten.
- Das Frontend-Image hat seine API-URL zur Build-Zeit ins Bundle kompiliert. Wenn das Frontend kein Backend findet, ist das vermutlich der Grund — Backend-Health-Check unter `http://localhost:8001/health` zeigt, ob das Backend selbst läuft.
- **Google Wallet ist im Abgabe-Setup deaktiviert.** Die Integration benötigt zur Laufzeit eine private Google-Service-Account-JSON-Datei, die wir nicht ins öffentlich zugängliche Bundle legen. Das Backend startet ohne diese Datei normal — nur die "Zum Google Wallet hinzufügen"-Funktion ist nicht aktiv.
