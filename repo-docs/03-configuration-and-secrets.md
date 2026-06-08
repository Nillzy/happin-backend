# Konfiguration und Geheimnisse

## Quelle der Wahrheit im Code

Die Klasse `Settings` in `app/core/config.py` (Pydantic `BaseSettings`) definiert, welche Variablen die Anwendung **tatsächlich** einliest. Standardmäßig wird eine Datei **`.env`** im Projektroot geladen (`env_file = ".env"`).

## Variablen (laut `Settings`)

| Variable | Pflicht | Bedeutung |
|----------|---------|-----------|
| `SUPABASE_URL` | Ja | Basis-URL des Supabase-Projekts |
| `SUPABASE_ANON_KEY` | Ja | Öffentlicher **Anon**-API-Key (Supabase Dashboard) |
| `SUPABASE_JWT_SECRET` | Nein | Reserviert für spätere/ergänzende JWT-Prüfungen; aktuell nicht zwingend für `get_user` |
| `DATABASE_URL` | Nein | Direkte Postgres-URL, falls ihr später SQLAlchemy o. Ä. nutzt |
| `DEBUG` | Nein (Default: `false`) | Steuert u. a. OpenAPI unter `/docs` und `redoc` |
| `LOG_LEVEL` | Nein | String, z. B. `info` |

## `.env.example`

Die Datei `.env.example` dient als **Vorlage** für lokale Entwicklung und sollte dieselben **Variablennamen** wie `Settings` verwenden (insbesondere **`SUPABASE_ANON_KEY`**, nicht ein generischer `SUPABASE_KEY`-Name, sofern der Code nicht per Alias mapped).

**Sicherheit:** Niemals echte Secrets committen. `.env` gehört in `.gitignore` (ist im Projekt üblich).

## Debug vs. Produktion

- **`DEBUG=true`:** Swagger UI unter `/docs`, ReDoc unter `/redoc`, ausführlichere Fehlerdarstellung möglich.
- **`DEBUG=false`:** Dokumentations-UI deaktiviert; für öffentliche Deployments empfohlen.

## Supabase-Client

`app/core/supabase.py` erzeugt den Client mit `SUPABASE_URL` und `SUPABASE_ANON_KEY`. Der Modulimport führt dabei die Client-Erzeugung aus; für lokale Tests ohne erreichbare Supabase-URL kann das beim Import zu Fehlern führen — dann Umgebung mocken oder URL/Key setzen.
