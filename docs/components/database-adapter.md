# DatabaseAdapter

**Kategorie:** T-Software  
**Entwurfs-Entsprechung:** `<<component>> DatabaseAdapter`  
**Implementierung:** `app/core/supabase.py`, Supabase Python-Client

## Beschreibung

Der `DatabaseAdapter` kapselt alle Datenbankzugriffe und schützt den Anwendungskern vor direkter Datenbankabhängigkeit. Er stellt dem Anwendungskern die Schnittstellen `Read` und `Write` (für Anwendungsdaten) sowie `Auth` (für Authentifizierungsoperationen) bereit.

Als konkreter Datenbankdienst wird **Supabase** eingesetzt, das eine gehostete PostgreSQL-Datenbank mit integrierter Auth, Row-Level Security (RLS) und REST-API bereitstellt.

[→ Im Architekturentwurf ansehen](<https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Entwurf/Komponentendiagramm#:~:text=Entfernung%2C%20Nachr%C3%BCcken%2C%20Erinnerungen)-,DatabaseAdapter,-M1%20(DBAuth%3A%20Nutzer>)

## Bereitgestellte Schnittstellen

| Schnittstelle | Genutzt von | Beschreibung |
|---|---|---|
| `Auth` (DBAuth) | Authentication | Nutzerauthentifizierung gegen die Datenbank |
| `Read` (DBData) | Anwendungskern | Datensätze lesen |
| `Write` (DBData) | Anwendungskern | Datensätze schreiben, aktualisieren, löschen |

## Genutzte Schnittstellen

- **`DBAuth`** – Supabase Auth (PostgreSQL auth-Schema)
- **`DBData`** – Supabase PostgreSQL-Datenbank

## Implementierung

### Client-Initialisierung (Lazy Singleton)

```python
# app/core/supabase.py
_client: Client | None = None

def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
    return _client
```

### Typische Zugriffsmuster

**Lesen:**
```python
client = get_supabase()
result = client.table("events").select("*").eq("id", event_id).execute()
```

**Schreiben:**
```python
result = client.table("events").insert(event_data).execute()
```

**Löschen:**
```python
client.table("events").delete().eq("id", event_id).execute()
```

### Row-Level Security (RLS)

Supabase RLS-Richtlinien sichern den Datenzugriff auf Datenbankebene ab. Z. B. kann ein Nutzer nur seine eigenen Tickets sehen, auch wenn das Backend keine explizite Filterung durchführt.

## Datenbanktabellen (Auswahl)

| Tabelle | Beschreibung |
|---|---|
| `events` | Event-Datensätze |
| `persons` | Nutzerprofile |
| `bookings` | Buchungen / RSVP-Einträge |
| `tickets` | Einzelne Tickets mit QR-Tokens |
| `ticket_options` | Preisstufen pro Event |
| `custom_fields` | Benutzerdefinierte Felder |
| `custom_field_responses` | Antworten auf Custom Fields |
| `notifications` | In-App-Benachrichtigungen |
| `reminder_subscriptions` | Push-Erinnerungsabonnements |
| `push_subscriptions` | Web-Push-Gerät-Tokens |
| `waitlist` | Wartelisten-Einträge |

## Abhängigkeiten

- Supabase (gehosteter Dienst) – `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`
