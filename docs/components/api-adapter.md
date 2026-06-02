# APIAdapter

**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> APIAdapter`  
**Implementierung:** `app/api/v1/`

## Beschreibung

Der `APIAdapter` ist die zentrale Eingangskomponente des Backends. Er empfängt alle HTTP-Anfragen der Frontend-Clients und leitet sie an die zuständigen Anwendungskern-Komponenten weiter. Er stellt sämtliche API-Schnittstellen bereit, die vom `BackendAdapter` des Frontends genutzt werden.

Im Entwurf ist der `APIAdapter` genau so realisiert wie vorgesehen: als einziger Zugangspunkt für alle Frontend-Anfragen, der intern an die jeweiligen Fachkomponenten delegiert.

## Bereitgestellte Schnittstellen

| Schnittstelle | Beschreibung | Router-Datei |
|---|---|---|
| `AuthAPI` | Authentifizierung, Account-Verwaltung | `user.py`, `users.py` |
| `EventInfoAPI` | Event-Details lesen | `events.py` |
| `EventAdminAPI` | Events erstellen, bearbeiten, absagen | `events.py` |
| `RSVPAPI` | RSVP-Status setzen und abfragen | `events.py` |
| `HostDashboardAPI` | Host-spezifische Ansichten | `events.py`, `users.py` |
| `NotificationAPI` | In-App-Benachrichtigungen | `notifications.py` |
| `PublicListAPI` | Öffentliche Event-Suche und -Liste | `events.py` |
| `TicketingAPI` | Tickets buchen, verwalten, scannen | `tickets.py`, `ticket_options.py` |

## Struktur

```
app/api/v1/
├── router.py           # Aggregiert alle Sub-Router unter /api/v1
├── user.py             # Auth-Debugging-Endpunkte
├── users.py            # Account-Verwaltung
├── events.py           # Events (öffentlich + Host)
├── tickets.py          # Ticketkauf und -verwaltung
├── ticket_options.py   # Preisoptionen (CRUD)
├── custom_fields.py    # Benutzerdefinierte Felder bei Events
├── payments.py         # Stripe Connect
├── images.py           # Unsplash-Proxy
├── reminders.py        # Push-Erinnerungen
└── notifications.py    # In-App-Benachrichtigungen
```

## Einstiegspunkt

Der aggregierende Router wird in `app/main.py` eingebunden:

```python
from app.api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")
```

## Abhängigkeiten

- Nutzt [`Authentication`](authentication.md) via FastAPI-Dependency `get_current_user()`
- Delegiert an alle [Anwendungskern-Komponenten](anwendungskern.md)
- Nutzt Pydantic-Schemas aus `app/schemas/` für Request-/Response-Validierung

## Authentifizierung

Geschützte Endpunkte verwenden die FastAPI-Dependency `get_current_user`:

```python
@router.get("/events/{event_id}")
async def get_event(
    event_id: str,
    current_user: dict = Depends(get_current_user_optional)
):
    ...
```
