# MapsAdapter

**Kategorie:** T-Software  
**Entwurfs-Entsprechung:** `<<component>> MapsAdapter`  
**Implementierung:** `app/services/geocoding_service.py`

## Beschreibung

Der `MapsAdapter` kapselt die Kommunikation mit dem externen Kartendienst **MapTiler**. Er stellt dem Anwendungskern die Schnittstelle `ConvertCoordinates` bereit, über die Adressen in geografische Koordinaten (Geocoding) umgewandelt werden.

Koordinaten werden beim Erstellen eines Events benötigt, damit der Ort auf der Karte angezeigt werden kann.

## Bereitgestellte Schnittstellen

| Schnittstelle | Genutzt von | Beschreibung |
|---|---|---|
| `ConvertCoordinates` | EventAdmin | Adresse → GPS-Koordinaten (Geocoding) |

## Genutzter externer Dienst

**MapTiler** (AT-Software) – Geocoding-API und Karten-Tiles.

## Implementierung

```python
# app/services/geocoding_service.py

async def geocode_address(
    street: str,
    city: str,
    country: str = "DE"
) -> tuple[float, float] | None:
    """
    Gibt (latitude, longitude) zurück oder None wenn nicht gefunden.
    Nutzt MapTiler Geocoding API v2.
    """
    url = f"https://api.maptiler.com/geocoding/{query}.json"
    params = {"key": settings.MAPTILER_KEY, "country": country}
    response = await httpx.get(url, params=params)
    features = response.json().get("features", [])
    if features:
        lon, lat = features[0]["geometry"]["coordinates"]
        return lat, lon
    return None
```

## Konfiguration

| Umgebungsvariable | Beschreibung |
|---|---|
| `MAPTILER_KEY` | API-Schlüssel für MapTiler |

## Abhängigkeiten

- MapTiler (AT-Software, externer Dienst)
