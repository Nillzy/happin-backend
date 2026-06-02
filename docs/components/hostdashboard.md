# HostDashboard

**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> HostDashboard` (im Anwendungskern)  
**Implementierung:** `app/services/user_service.py`, `app/services/person_service.py`

## Beschreibung

Die `HostDashboard`-Komponente stellt alle Host-spezifischen Ansichten und Verwaltungsfunktionen bereit. Ein Host kann seine eigenen Events einsehen, die Teilnehmerliste verwalten, RSVP-Antworten prüfen und Tickets scannen.

## Bereitgestellte Schnittstellen

| Schnittstelle | Endpunkt | Beschreibung |
|---|---|---|
| `HostDashboard` (Events) | `GET /api/v1/users/events` | Alle vom Host erstellten Events |
| `HostDashboard` (Stats) | `GET /api/v1/users/stats` | Statistiken (Events, Buchungen, Einnahmen) |
| `HostDashboard` (Participants) | `GET /api/v1/events/{id}/participants` | Teilnehmerliste eines Events |
| `HostDashboard` (Scan) | `POST /api/v1/events/{id}/scan` | Ticket-QR-Code einlesen und validieren |
| `HostDashboard` (RSVP-Antworten) | `GET /api/v1/events/{id}/rsvp` | RSVP-Zusagen und -Absagen |

## Genutzte Schnittstellen

- **`Read`** (DatabaseAdapter): Lädt Events, Teilnehmerlisten, Buchungsdaten

## Implementierung

### Host-Events

```python
# app/services/user_service.py
async def get_host_events(user_id: str) -> list[EventListItem]:
    # Alle Events bei denen person_id == user_id
    # Sortiert nach start_time absteigend
```

### Teilnehmerliste (Participants)

```python
# app/services/person_service.py
async def get_participants(
    event_id: str,
    host_id: str
) -> ParticipantListResponse:
    # 1. Host-Berechtigung prüfen
    # 2. Alle bestätigten Buchungen laden
    # 3. Nutzerdaten (Name, E-Mail) ergänzen
    # 4. Custom-Field-Antworten je Teilnehmer ergänzen
```

### Host-Statistiken

```python
class UserStats(BaseModel):
    total_events_hosted: int
    total_tickets_sold: int
    total_revenue: float          # Stripe-Auszahlungen
    upcoming_events: int
    past_events: int
```

## Sicherheit

Alle HostDashboard-Endpunkte erfordern Authentifizierung und prüfen, dass der anfragende Nutzer tatsächlich Host des betreffenden Events ist.

## Abhängigkeiten

- [`DatabaseAdapter`](database-adapter.md)
- [`Ticketing`](ticketing.md) – für Ticket-Scan-Validierung
