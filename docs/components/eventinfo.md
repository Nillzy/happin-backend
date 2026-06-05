# EventInfo

**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> EventInfo` (im Anwendungskern)  
**Implementierung:** `app/services/event_service.py` (Lese-Operationen), `app/services/weather_service.py`

## Beschreibung

Die `EventInfo`-Komponente stellt detaillierte Informationen zu einzelnen Events bereit. Sie wird vom `APIAdapter` über die `EventInfoAPI`-Schnittstelle aufgerufen und liefert Event-Details an das Frontend.

[→ Im Architekturentwurf ansehen](<https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Entwurf/Komponentendiagramm#:~:text=Validierung%2C%20Account%2DErstellung)-,EventInfo,-M4%20(Eindeutige%2C%20nicht>)

## Bereitgestellte Schnittstellen

| Schnittstelle | Endpunkt | Beschreibung |
|---|---|---|
| `EventInfo` | `GET /api/v1/events/{event_id}` | Vollständige Event-Details inkl. Ticket-Optionen, Wetter, RSVP-Status |

## Genutzte Schnittstellen

- **`Read`** (DatabaseAdapter): Liest Event-Datensatz, Ticket-Optionen, RSVP-Status des anfragenden Nutzers
- **`GetWeather`** (WeatherAdapter): Liefert Wettervorhersage für Ort und Datum des Events

## Implementierung

### Kern-Funktion

```python
# app/services/event_service.py
async def get_event_by_id(
    event_id: str,
    current_user: dict | None = None
) -> EventDetailResponse:
    # 1. Event-Datensatz laden
    # 2. Ticket-Optionen laden
    # 3. RSVP-Status des Nutzers laden (falls auth)
    # 4. Wetter für Eventdatum laden
    # 5. Ortsdetails (Adresse, Koordinaten) zusammenstellen
    # 6. Privatsphäre: genaue Adresse nur für angemeldete Nutzer
```

### Ortsabstraktion

Nicht angemeldete Nutzer erhalten nur den Stadtteil, keine genaue Adresse:

```python
def _filter_location_for_public(event: dict) -> dict:
    # Entfernt street, house_number für anonyme Anfragen
    ...
```

## Datenmodell (Response)

```python
class EventDetailResponse(BaseModel):
    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: LocationDetail
    categories: list[str]
    ticket_options: list[TicketOption]
    rsvp_status: str | None      # nur bei auth
    weather: WeatherForecast | None
    image_urls: list[str]
    is_cancelled: bool
    host: HostInfo
```

## Abhängigkeiten

- [`DatabaseAdapter`](database-adapter.md) – Datenbankzugriff
- [`WeatherAdapter`](weather-adapter.md) – Wettervorhersage
