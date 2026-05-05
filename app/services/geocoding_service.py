"""MapTiler Forward Geocoding — gibt (lat, lng) für eine Adresse zurück."""

import logging
import urllib.parse
import urllib.request
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

_GEOCODING_BASE = "https://api.maptiler.com/geocoding"


def geocode_address(
    street: str | None,
    house_number: str | None,
    postal_code: str | None,
    city: str | None,
    country: str | None,
) -> tuple[float, float] | None:
    """Gibt (latitude, longitude) zurück oder None bei Fehler / fehlendem Key."""
    if not settings.MAPTILER_KEY:
        return None

    parts = []
    if street and house_number:
        parts.append(f"{street} {house_number}")
    elif street:
        parts.append(street)
    if postal_code and city:
        parts.append(f"{postal_code} {city}")
    elif city:
        parts.append(city)
    if country:
        parts.append(country)

    if not parts:
        return None

    query = urllib.parse.quote(", ".join(parts))
    url = f"{_GEOCODING_BASE}/{query}.json?key={settings.MAPTILER_KEY}&limit=1"

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        features = data.get("features") or []
        if not features:
            return None
        coords = features[0]["geometry"]["coordinates"]
        return (coords[1], coords[0])  # (lat, lng)
    except Exception as exc:
        logger.warning("Geocoding fehlgeschlagen für '%s': %s", ", ".join(parts), exc)
        return None
