# 23. Weather Forecast Integration (S3)

**Pflichtenheft-Anforderung S3 – Wetteranzeige:**  
Hosts können pro Event einstellen, dass die aktuelle Wettervorhersage für den Veranstaltungsort und -zeitpunkt angezeigt wird.

## Überblick

Die Wettervorhersage-Funktion ermöglicht es Hosts, Teilnehmern hilfreiche Informationen über das erwartete Wetter am Event-Tag zu zeigen. Die Funktion ist optional und kann vom Host beim Erstellen oder in den Event-Einstellungen aktiviert werden.

**Datenquelle:** WeatherAPI.com (siehe Projektrecherche in `happin.wiki/Requirement-Engineering/WIE-Ebene/Research/Weather-Service.md`)

**Vorteile von WeatherAPI.com:**
- Großzügiges Free-Tier: 1 Million Requests/Monat
- 3-Tage-Forecast kostenlos (ausreichend für Event-Planung)
- Stündliche Vorhersagen mit allen benötigten Daten
- Deutsche Lokalisierung (`lang=de`)
- Einfache REST-API

## Datenbankschema

**Migration:** `20260526000002_add_show_weather_forecast.sql`

```sql
ALTER TABLE event 
ADD COLUMN IF NOT EXISTS show_weather_forecast BOOLEAN DEFAULT false;
```

**Feld:**
- `show_weather_forecast` (BOOLEAN, DEFAULT false) — Host-Setting für Wetteranzeige

## Backend-Architektur

### Konfiguration

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    # ...
    WEATHERAPI_KEY: str | None = None
```

**Environment Variable:**
```bash
WEATHERAPI_KEY=your_api_key_here  # Optional, Feature deaktiviert wenn nicht gesetzt
```

API-Key erhalten unter: https://www.weatherapi.com/signup.aspx

### Adapter Layer

**File:** `app/adapters/weatherapi.py`

Implementiert HTTP-Client für WeatherAPI.com:

```python
def get_weather_forecast(lat: float, lon: float, dt: datetime | str) -> dict | None:
    """
    Fetch weather forecast from WeatherAPI.com.
    
    Args:
        lat: Latitude of event location
        lon: Longitude of event location
        dt: Event start datetime (datetime object or ISO string)
    
    Returns:
        {
            "temp_c": 22.5,
            "condition": "Partly cloudy",
            "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png",
            "humidity": 65,
            "wind_kph": 12.5,
            "chance_of_rain": 10
        }
        or None if API unavailable
    """
```

**API-Endpoint:**
```
GET https://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={lat},{lon}&dt={date}&lang=de
```

**Besonderheiten:**
- Akzeptiert sowohl `datetime`-Objekte als auch ISO-Strings als `dt`-Parameter
- Konvertiert ISO-Strings automatisch zu datetime für Zeitvergleich
- Findet die Stunde im Forecast, die am nächsten zur Event-Startzeit liegt
- Gibt `None` zurück bei Fehlern (keine Exception), für graceful degradation

### Service Layer

**File:** `app/services/weather_service.py`

Business Logic Wrapper:

```python
def get_event_weather(lat: float | None, lon: float | None, starts_at: datetime) -> dict | None:
    """
    Get weather forecast for event location and time.
    Returns None if coordinates missing or API unavailable.
    """
```

**Validierung:**
- Prüft ob Koordinaten vorhanden sind
- Delegiert an Adapter
- Keine Caching-Schicht (Wetter ändert sich, 1M requests/Monat ausreichend)

### API Integration

**File:** `app/api/v1/events.py`

**Schema-Erweiterungen:**

```python
# EventCreate
class EventCreate(BaseModel):
    # ...
    show_weather_forecast: bool = False

# EventUpdate
class EventUpdate(BaseModel):
    # ...
    show_weather_forecast: bool | None = None

# EventDetailResponse
class EventDetailResponse(BaseModel):
    # ...
    show_weather_forecast: bool = False
    weather_forecast: dict | None = None
```

**Weather-Fetch in `_to_detail()` Helper:**

```python
def _to_detail(raw: dict, supabase_user_id: str | None) -> EventDetailResponse:
    # ... existing code ...
    
    # Fetch weather forecast if enabled
    weather_forecast = None
    if raw.get("show_weather_forecast"):
        loc = raw.get("location") or {}
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        starts_at = raw.get("starts_at")
        if lat and lon and starts_at:
            weather_forecast = weather_service.get_event_weather(lat, lon, starts_at)
    
    return EventDetailResponse(
        # ...
        show_weather_forecast=raw.get("show_weather_forecast", False),
        weather_forecast=weather_forecast,
    )
```

**Logik:**
- Wetter wird nur gefetcht wenn `show_weather_forecast = true`
- Nur wenn Koordinaten vorhanden (erfordert gültige Adresse)
- On-demand bei Event-Detail-Abfrage (kein Caching)
- Fehler führen zu `weather_forecast: null`, nicht zu API-Error

### Graceful Degradation

Das Feature ist so designed, dass es niemals einen Request zum Scheitern bringt:

1. **Kein API-Key:** `weather_forecast: null` in Response
2. **Keine Koordinaten:** `weather_forecast: null` (Event ohne vollständige Adresse)
3. **API-Timeout/Fehler:** `weather_forecast: null` (geloggt, aber kein 500-Error)
4. **Feature deaktiviert:** `show_weather_forecast: false`, kein API-Call

## Frontend-Integration

### Komponenten

**WeatherBlock Component:** `frontend/src/components/event/WeatherBlock.tsx`

Zeigt Wettervorhersage mit:
- Wetter-Icon (von WeatherAPI CDN)
- Temperatur in °C
- Wetterbeschreibung (deutsch)
- Details: Regenwahrscheinlichkeit, Wind, Luftfeuchtigkeit
- Standort-Badge mit Stadt

**Icons:** Verwendet Ionicons (`water-outline`, `leaf-outline`) statt Emojis

### Event-Anzeige

**EventScreen:** Zeigt WeatherBlock unter der Karte, wenn:
- `event.show_weather_forecast === true`
- `event.weather_forecast` vorhanden (nicht null)

### Host-Controls

**Event-Erstellung (Seite 2):** `EventCreateStepTwo.tsx`
- Toggle erscheint nach Adresseingabe (unter Karten-Vorschau)
- Nur sichtbar wenn Adresse mit Koordinaten vorhanden
- Standard: deaktiviert

**Event-Einstellungen:** `EventEditScreen.tsx`
- Toggle in Settings-Drawer
- Icon: `partly-sunny-outline`
- Änderung wird via PATCH-Endpoint gespeichert

### TypeScript Types

**File:** `frontend/src/types/events.ts`

```typescript
interface EventDetailResponse {
    // ...
    show_weather_forecast?: boolean;
    weather_forecast?: {
        temp_c: number;
        condition: string;
        icon: string;
        humidity: number;
        wind_kph: number;
        chance_of_rain: number;
    } | null;
}
```

## API-Verwendung

### Event mit Wetter erstellen

```bash
POST /api/v1/events
Authorization: Bearer {token}
Content-Type: application/json

{
    "title": "Sommerparty",
    "starts_at": "2026-07-15T18:00:00+02:00",
    "is_public": true,
    "show_weather_forecast": true,
    "location": {
        "city": "Berlin",
        "latitude": 52.520008,
        "longitude": 13.404954
    }
}
```

### Wetter-Toggle ändern

```bash
PATCH /api/v1/events/{event_id}
Authorization: Bearer {token}
Content-Type: application/json

{
    "show_weather_forecast": true
}
```

### Event-Details mit Wetter abrufen

```bash
GET /api/v1/events/{event_id}

Response:
{
    "event_id": "...",
    "title": "Sommerparty",
    "show_weather_forecast": true,
    "weather_forecast": {
        "temp_c": 24.5,
        "condition": "Teilweise bewölkt",
        "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png",
        "humidity": 65,
        "wind_kph": 12.5,
        "chance_of_rain": 10
    },
    "location": {
        "city": "Berlin",
        ...
    }
}
```

## Rate Limits & Performance

**WeatherAPI Free Tier:**
- 1 Million Requests/Monat
- ~1370 Requests/Stunde bei gleichmäßiger Verteilung
- 3-Tage-Forecast inklusive

**Aktuelles Design:**
- On-demand fetch bei Event-Detail-Request
- Kein Caching (Wetter ändert sich)
- Timeout: 5 Sekunden

**Bei Überschreitung des Limits:**
- API gibt 429-Error
- Backend loggt Warning
- Response enthält `weather_forecast: null`
- Event bleibt sichtbar (keine Fehlerseite)

**Zukünftige Optimierungen (bei Bedarf):**
- Redis-Cache mit 6h TTL (Pflichtenheft-Anforderung)
- Batch-Update für populäre Events
- Fallback auf andere Weather-API

## Testing

**Manual Testing:**

1. Backend ohne `WEATHERAPI_KEY` starten:
   - Wetter-Toggle im Frontend funktioniert
   - `weather_forecast` ist immer `null`

2. Mit gültigem API-Key:
   - Event mit Adresse erstellen
   - Toggle aktivieren
   - Event-Details abrufen → Wetter erscheint

3. Edge Cases:
   - Event ohne Koordinaten → kein Wetter
   - Event in 4 Tagen → außerhalb 3-Tage-Forecast → `null`
   - Ungültige Koordinaten → API-Error → `null`

**Integration Tests (TODO):**
- Mock WeatherAPI responses
- Test `_to_detail()` mit/ohne weather flag
- Test graceful degradation

## Sicherheit

**Kein direkter Frontend-Zugriff:**
- API-Key nur im Backend
- Frontend kann nicht direkt WeatherAPI aufrufen
- Verhindert Key-Leakage und Rate-Limit-Abuse

**Input Validation:**
- Koordinaten kommen aus Geocoding-Service (MapTiler)
- DateTime-Format validiert durch Pydantic
- Keine User-Inputs direkt in Weather-API-URL

## Dokumentations-Updates

Nach Feature-Implementierung:
- [x] Backend-Dokumentation (diese Datei)
- [x] Index aktualisiert (`00-index.md`)
- [x] `.env.example` erweitert
- [x] AGENTS.md ergänzt (Backend)
- [ ] Frontend DESIGN.md (WeatherBlock UI-Specs)
- [ ] E2E-Test-Dokumentation

## Weitere Verbesserungen

**Nice-to-have (zukünftig):**
- [ ] 6h-Cache mit Redis (Pflichtenheft S3)
- [ ] Admin-Dashboard: Weather-API-Usage-Stats
- [ ] A/B-Test: Einfluss von Wetter-Anzeige auf RSVP-Rate
- [ ] Wetter-basierte Event-Recommendations ("Indoor-Events für Regentage")
- [ ] Push-Notification bei Wetteränderung
