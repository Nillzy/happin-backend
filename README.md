# Happin Backend

FastAPI Backend für die Happin Event-Discovery Plattform.

## Quick Start für neue Team-Mitglieder

```bash
# 1. Repository clonen
git clone https://gitlab.com/dhbw-se/se-tinf24b2/happin/backend.git
cd backend

# 2. Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. Environment Variables einrichten
cp .env.example .env
# Öffne .env und fülle API Keys ein (frag Team nach Test-Keys!)

# 5. Server starten
uvicorn main:app --reload --port 8001
# Backend läuft auf: http://localhost:8001
# API Docs: http://localhost:8001/docs
```

**Fertig! Backend läuft mit Hot Reload.**

---

## Tech Stack

- **Framework:** FastAPI
- **Python:** 3.11+
- **Server:** Uvicorn (ASGI)
- **Database:** Supabase PostgreSQL
- **External APIs:** Twilio Verify, Stripe, MapTiler, WeatherAPI

## Lokale Entwicklung

### Voraussetzungen

- Python 3.11 oder höher
- pip

### Setup

1. **Virtual Environment erstellen:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # oder
   venv\Scripts\activate  # Windows
   ```

2. **Dependencies installieren:**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Neue Bibliothek hinzufügen:**
   - Bibliothek manuell in `requirements.txt` eintragen
   - Beispiel: `stripe>=7.0.0`
   - Dann: `pip install -r requirements.txt`

3. **Environment Variables konfigurieren:**
   ```bash
   cp .env.example .env
   # .env File mit echten API Keys befüllen
   ```
   
   **Wichtig:** 
   - `.env` ist in `.gitignore` und wird NICHT committed!
   - Neue Variable hinzugefügt? → Manuell auf VM in `/home/shared/deployment/backend/.env` eintragen!

4. **Server starten:**
   ```bash
   uvicorn main:app --reload --port 8001
   ```

5. **API Dokumentation öffnen:**
   - Swagger UI: http://localhost:8001/docs
   - ReDoc: http://localhost:8001/redoc

## Docker

### Build & Run

```bash
# Image bauen
docker build -t happin-backend .

# Container starten
docker run -p 8001:8001 --env-file .env --add-host host.docker.internal:host-gateway happin-backend
```

### Mit Docker Compose (empfohlen)

```bash
cd ..  # Root-Verzeichnis
docker-compose up backend
```

## Environment Variables

Siehe [`.env.example`](.env.example) für alle erforderlichen Variablen:

- `DATABASE_URL` - PostgreSQL Connection String
- `SUPABASE_URL` & `SUPABASE_KEY` - Supabase Konfiguration
- `TWILIO_*` - SMS/WhatsApp OTP
- `STRIPE_SECRET_KEY` - Payment Processing
- `MAPTILER_API_KEY` - Maps & Geocoding
- `WEATHER_API_KEY` - Weather Forecasts

**Wichtig:** `.env` Files niemals ins Git committen!

## CI/CD

GitLab CI/CD Pipeline baut automatisch Docker Images bei Push zu `main`:

- **Build Stage:** Docker Image wird gebaut und zu GitLab Container Registry gepusht
- **Deploy Stage:** Manuelles Deployment zur VM (`when: manual`)

### GitLab Variables (zu setzen in GitLab UI)

- `SSH_PRIVATE_KEY` - SSH Key für VM Deployment

## API Endpoints

Sobald implementiert, siehe Swagger UI unter `/docs` für vollständige API-Dokumentation.

## Entwicklung

### Code Structure (geplant)

```
backend/
├── main.py              # FastAPI Entry Point
├── api/                 # API Endpoints
├── services/            # Business Logic
├── adapters/            # External Service Adapters
│   ├── database.py      # Supabase
│   ├── messaging.py     # Twilio
│   ├── payment.py       # Stripe
│   └── ...
├── models/              # Pydantic Models
└── requirements.txt
```

## License

DHBW SE Project - Happin Team
