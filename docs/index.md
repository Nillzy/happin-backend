# Happin Backend – Dokumentation

Happin ist eine Eventplattform, auf der Nutzer Events entdecken, erstellen, buchen und verwalten können. Dieses Dokument beschreibt die Architektur und die Komponenten des **Happin-Backends**.

## Technologie-Stack

| Komponente | Technologie |
|---|---|
| Web-Framework | FastAPI 0.109 |
| Laufzeit | Python 3.11, Uvicorn |
| Datenbank | Supabase (PostgreSQL) |
| Authentifizierung | Supabase Auth (JWT) |
| Zahlung | Stripe Connect |
| E-Mail | Resend |
| Karten | MapTiler |
| Wetter | WeatherAPI.com |
| Push-Benachrichtigungen | Web Push (VAPID) + Expo Push |
| PDF-Erzeugung | ReportLab |
| Scheduler | APScheduler |
| Tests | pytest + httpx |

## Schnellstart

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Umgebungsvariablen setzen
cp .env.example .env
# .env befüllen

# Entwicklungsserver starten
uvicorn app.main:app --reload --port 8001
```

## Projektstruktur

```
happin-backend/
├── app/
│   ├── main.py               # FastAPI-Einstiegspunkt
│   ├── core/                 # Konfiguration, Auth, Supabase-Client
│   ├── api/v1/               # HTTP-Router (thin wrappers)
│   ├── services/             # Business-Logik
│   ├── schemas/              # Pydantic-Validierungsmodelle
│   └── adapters/             # Externe-Dienst-Adapter
├── tests/                    # pytest-Testsuite
├── requirements.txt
├── Dockerfile
└── mkdocs.yml
```

## Weiterführende Abschnitte

- [Architekturentwurf](architecture.md) – Komponentendiagramm und Entwurfsvergleich
- [Komponenten](components/index.md) – Jede Komponente auf einer eigenen Seite
- [API-Referenz](/api/docs) – Interaktive Swagger-UI mit allen Endpunkten
