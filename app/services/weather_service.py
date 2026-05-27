"""Weather service — business logic for event weather forecasts."""

from datetime import datetime
from app.adapters import weatherapi


def get_event_weather(lat: float | None, lon: float | None, starts_at: datetime) -> dict | None:
    """
    Get weather forecast for event location and time.

    Args:
        lat: Latitude of event location (can be None)
        lon: Longitude of event location (can be None)
        starts_at: Event start datetime

    Returns:
        Weather forecast dict from WeatherAPI adapter, or None if:
        - Coordinates are missing
        - API key not configured
        - API request fails
    """
    if not lat or not lon:
        return None

    return weatherapi.get_weather_forecast(lat, lon, starts_at)
