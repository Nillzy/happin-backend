# WeatherAdapter

**Kategorie:** T-Software  
**Entwurfs-Entsprechung:** `<<component>> WeatherAdapter`  
**Implementierung:** `app/adapters/weatherapi.py`, `app/services/weather_service.py`

## Beschreibung

Der `WeatherAdapter` kapselt die Kommunikation mit dem externen Wetterdienst **WeatherAPI.com**. Er stellt dem Anwendungskern (konkret: `EventInfo`) die Schnittstelle `GetWeather` bereit, über die Wettervorhersagen für Event-Orte und -Zeitpunkte abgerufen werden.

## Bereitgestellte Schnittstellen

| Schnittstelle | Genutzt von | Beschreibung |
|---|---|---|
| `GetWeather` | EventInfo | Wettervorhersage für Ort + Datum abrufen |

## Genutzter externer Dienst

**WeatherAPI.com** (AT-Software) – Stündliche Wettervorhersage für beliebige Koordinaten.

## Implementierung

### Adapter (`weatherapi.py`)

```python
# app/adapters/weatherapi.py

async def get_weather_forecast(
    lat: float,
    lon: float,
    event_date: date
) -> WeatherForecast | None:
    """
    Liefert Wettervorhersage für Koordinaten und Datum.
    Nur verfügbar für Events innerhalb der nächsten 14 Tage.
    """
    url = "https://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": settings.WEATHERAPI_KEY,
        "q": f"{lat},{lon}",
        "dt": event_date.isoformat(),
        "hour": event_hour
    }
```

### Datenmodell (Response)

```python
class WeatherForecast(BaseModel):
    temperature_c: float        # Temperatur in °C
    condition: str              # z. B. "Partly cloudy"
    condition_icon: str         # URL zum Wetter-Icon
    humidity: int               # Luftfeuchtigkeit in %
    wind_kph: float             # Windgeschwindigkeit in km/h
    chance_of_rain: int         # Regenwahrscheinlichkeit in %
```

## Einschränkungen

- Vorhersagen sind nur für Events in den nächsten **14 Tagen** verfügbar
- Bei weiter entfernten Events gibt `GetWeather` `None` zurück

## Konfiguration

| Umgebungsvariable | Beschreibung |
|---|---|
| `WEATHERAPI_KEY` | API-Schlüssel für WeatherAPI.com |

## Abhängigkeiten

- WeatherAPI.com (AT-Software, externer Dienst)
