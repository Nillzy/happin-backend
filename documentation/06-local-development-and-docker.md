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

## Supabase CLI

Die Supabase CLI ist ein eigenes Kommandozeilen-Tool (Go-Binary), kein Python-Paket und steht nicht in `requirements.txt`.

### CLI installieren

- macOS (empfohlen): [Homebrew](https://brew.sh/), offizielles Tap:
  ```bash
  brew install supabase/tap/supabase
  ```
- npm (global), wenn ohnehin Node.js genutzt wird:
  ```bash
  npm install -g supabase
  ```

Prüfen:

```bash
supabase --version
```

### Einmalige Einrichtung für das Team-Projekt

1. In die CLI einloggen:
  ```bash
   supabase login
  ```
2. Lokales Repo mit dem Remote-Projekt verknüpfen.
  - Team-Projekt: **HappinDB**
  - Project Reference: `hylnqapjtkgqyxvmfqgy`
  - Ausführen:
  ```bash
  supabase link --project-ref hylnqapjtkgqyxvmfqgy
  ```
3. Prüfen, ob alles geklappt hat:
  ```bash
  supabase projects list
  ```

### Grundlegende Befehle

| Befehl | Was er tut |
|--------|------------|
| `supabase login` | Authentifiziert die CLI mit deinem Supabase-Account |
| `supabase link --project-ref <ref>` | Verknüpft das lokale Repo mit einem Remote-Projekt |
| `supabase projects list` | Zeigt alle Projekte deines Accounts |
| `supabase db pull` | Zieht das aktuelle Remote-Schema als neue Migration |
| `supabase db push` | Wendet lokale Migrations auf die Remote-DB an |
| `supabase migration list` | Zeigt den Status aller Migrations (lokal vs. remote) |
| `supabase migration new <name>` | Erstellt eine leere Migration-Datei |
| `supabase migration repair --status applied <version>` | Markiert eine Migration manuell als applied |

### Migrations — wie sie funktionieren

Migrations sind SQL-Dateien unter `supabase/migrations/`. Jede Datei hat einen Zeitstempel-Prefix als Versionsnummer (z.B. `20260428140517_remote_schema.sql`). Supabase führt sie in chronologischer Reihenfolge aus und merkt sich in einer internen Tabelle (`supabase_migrations.schema_migrations`), welche schon angewendet wurden.

**Schema von Remote holen (db pull):**

```bash
supabase db pull
```

Das vergleicht das Remote-Schema mit dem lokalen Stand und erzeugt eine neue Migration-Datei mit den Unterschieden. Nutzt man das zum ersten Mal, enthält die Datei das komplette Schema.

**Lokale Änderungen schreiben:**

1. Neue Migration erstellen:
   ```bash
   supabase migration new add_ratings_table
   ```
   Das erzeugt eine leere Datei, z.B. `supabase/migrations/20260428150000_add_ratings_table.sql`.

2. SQL eintragen (CREATE TABLE, ALTER TABLE, etc.)

3. Auf die Remote-DB anwenden:
   ```bash
   supabase db push
   ```

**Typischer Workflow im Team:**

1. `git pull` — lokale Migrations aktuell halten
2. Schema-Änderung entweder:
   - Im Supabase Dashboard machen → `supabase db pull` zum Runterladen
   - Oder lokal als Migration-SQL schreiben → `supabase db push` zum Hochladen
3. Migration-Datei committen und pushen
4. Andere Teammitglieder: `git pull` → `supabase db push` um ihr Remote-Schema zu synchronisieren

**Wenn Migrations nicht übereinstimmen:**

Falls `supabase db pull` mit einem History-Mismatch fehlschlägt:
```bash
supabase migration repair --status applied <version>
```
Das markiert die genannte Version in der Remote-History als "applied", ohne sie nochmal auszuführen.

**Ordnerstruktur:**

```
supabase/
  config.toml                              # Supabase-Projektkonfiguration
  .temp/                                   # Interne CLI-Metadaten (nicht committen)
  migrations/
    20260423135813_remote_schema.sql        # Initiales Schema
    20260428140517_remote_schema.sql        # Aktualisiertes Schema
```

> **Wichtig:** Die Dateien unter `supabase/.temp/` sind lokal und maschinenspezifisch. Sie sollten in `.gitignore` stehen und nicht committed werden.

## Server starten

### Standard (localhost only)

```bash
uvicorn app.main:app --reload --port 8001
```

- API-Wurzel: `http://localhost:8001/`
- Health: `http://localhost:8001/health`
- Mit `DEBUG=true`: `http://localhost:8001/docs`

### Für physische Geräte (iPhone/Android)

Wenn du die Frontend-App auf einem physischen Gerät testen willst (z.B. via Expo Go), kann das Gerät nicht auf `localhost` zugreifen. Du hast zwei Optionen:

#### Option 1: ngrok Tunnel (Empfohlen)

ngrok erstellt einen öffentlichen Tunnel zu deinem lokalen Backend und umgeht Firewall-Probleme:

1. **Backend auf 0.0.0.0 starten** (akzeptiert externe Verbindungen):
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

2. **ngrok Tunnel starten** (separates Terminal):
   ```bash
   ngrok http 8001
   ```
   
   Output:
   ```
   Forwarding  https://abc-xyz-123.ngrok-free.dev -> http://localhost:8001
   ```

3. **Frontend `.env.local` aktualisieren**:
   ```
   EXPO_PUBLIC_BACKEND_URL=https://abc-xyz-123.ngrok-free.dev
   ```

4. **Frontend neu starten** (damit neue URL geladen wird)

**Hinweis:** Die ngrok-URL ändert sich bei jedem Neustart. Für eine feste URL brauchst du einen kostenpflichtigen ngrok-Account.

**Vorteile:**
- Funktioniert immer (umgeht Firewall)
- Kein Netzwerk-Setup nötig
- Auch außerhalb des lokalen WLANs nutzbar

**Nachteile:**
- Langsamer als direkte Verbindung (~100-300ms Latenz)
- URL ändert sich bei jedem Neustart

#### Option 2: Lokale IP-Adresse (schneller, erfordert Firewall-Konfiguration)

1. **Backend auf 0.0.0.0 starten**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

2. **Mac IP-Adresse finden**:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```
   Beispiel: `172.16.73.155`

3. **macOS Firewall konfigurieren**:
   - **Systemeinstellungen → Netzwerk → Firewall → Optionen**
   - Python hinzufügen und eingehende Verbindungen erlauben

4. **Frontend `.env.local` aktualisieren**:
   ```
   EXPO_PUBLIC_BACKEND_URL=http://172.16.73.155:8001
   ```

5. **Mac und Gerät im gleichen WLAN**

**Vorteile:**
- Schneller als ngrok (keine zusätzliche Latenz)
- Stabile URL (ändert sich nur, wenn sich die IP ändert)

**Nachteile:**
- Firewall muss konfiguriert werden
- Nur im gleichen WLAN nutzbar

## Docker (lokal)

```bash
docker build -t happin-backend .
docker run -p 8001:8001 --env-file .env happin-backend
```

Das Image startet Uvicorn auf **Port 8001**. Ein **HEALTHCHECK** ruft `GET /health` auf dem Container auf.

## Was nicht im Image liegt

Die Datei `.dockerignore` schließt unter anderem `documentation/` aus dem Build-Kontext aus. Die Markdown-Doku bleibt im Git-Repository für Menschen; sie muss nicht im Container vorliegen.

## Monorepo / Compose

Im README ist beschrieben, das Backend ggf. aus dem übergeordneten Verzeichnis per `docker-compose` zu starten (`docker-compose up backend`). Das liegt außerhalb dieses Backend-Repos; dort gelten die Compose-Dateien des Gesamtprojekts.