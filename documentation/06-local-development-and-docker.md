# Lokale Entwicklung und Docker

## Voraussetzungen

- Python **3.11+**
- `pip`
- Optional: **Docker**, wenn ihr das Image bauen oder wie in CI deployen wollt

## Virtuelle Umgebung und Dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Umgebung

```bash
cp .env.example .env
# Werte für SUPABASE_URL und SUPABASE_ANON_KEY setzen (siehe 03-configuration-and-secrets.md)
```

## Server starten

```bash
uvicorn app.main:app --reload --port 8001
```

- API-Wurzel: `http://localhost:8001/`
- Health: `http://localhost:8001/health`
- Mit `DEBUG=true`: `http://localhost:8001/docs`

## Docker (lokal)

```bash
docker build -t happin-backend .
docker run -p 8001:8001 --env-file .env happin-backend
```

Das Image startet Uvicorn auf **Port 8001**. Ein **HEALTHCHECK** ruft `GET /health` auf dem Container auf.

## Was nicht im Image liegt

Die Datei **`.dockerignore`** schließt u. a. **`documentation/`** aus dem Build-Kontext aus. Die Markdown-Doku bleibt im Git-Repository für Menschen; sie muss nicht im Container vorliegen.

## Monorepo / Compose

Im README ist beschrieben, das Backend ggf. aus dem **übergeordneten** Verzeichnis per `docker-compose` zu starten (`docker-compose up backend`). Das liegt außerhalb dieses Backend-Repos; dort gelten die Compose-Dateien des Gesamtprojekts.
