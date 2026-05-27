"""WeatherAPI.com adapter — provides weather forecasts for event locations."""

import logging
import urllib.request
import urllib.parse
import json
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

_WEATHERAPI_BASE = "https://api.weatherapi.com/v1"


def get_weather_forecast(lat: float, lon: float, dt: datetime | str) -> dict | None:
    """
    Fetch weather forecast from WeatherAPI.com for a specific location and time.

    Args:
        lat: Latitude of event location
        lon: Longitude of event location
        dt: Event start datetime (datetime object or ISO string)

    Returns:
        {
            "temp_c": 22.5,  # Celsius
            "condition": "Partly cloudy",  # Human-readable condition
            "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png",  # Icon URL
            "humidity": 65,  # %
            "wind_kph": 12.5,  # km/h
            "chance_of_rain": 10  # %
        }
        or None if API unavailable or error
    """
    if not settings.WEATHERAPI_KEY:
        logger.debug("WeatherAPI key not configured, skipping forecast")
        return None

    # Convert string to datetime if needed
    if isinstance(dt, str):
        from datetime import datetime as dt_class
        dt = dt_class.fromisoformat(dt.replace('Z', '+00:00'))

    # Use Forecast API (free tier: 3 days, up to 1M requests/month)
    # Format: YYYY-MM-DD for date parameter
    date_str = dt.strftime('%Y-%m-%d')
    url = f"{_WEATHERAPI_BASE}/forecast.json?key={settings.WEATHERAPI_KEY}&q={lat},{lon}&dt={date_str}&lang=de"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())

            # Find the hour closest to event start time
            target_hour = dt.hour
            forecast_day = data.get("forecast", {}).get("forecastday", [])

            if not forecast_day:
                logger.warning("No forecast data returned for %s at %s,%s", date_str, lat, lon)
                return None

            hours = forecast_day[0].get("hour", [])
            if not hours:
                logger.warning("No hourly forecast data for %s", date_str)
                return None

            # Find closest hour to event time
            closest_hour = min(
                hours,
                key=lambda h: abs(int(h["time"].split()[1].split(":")[0]) - target_hour)
            )

            return {
                "temp_c": closest_hour["temp_c"],
                "condition": closest_hour["condition"]["text"],
                "icon": closest_hour["condition"]["icon"],
                "humidity": closest_hour["humidity"],
                "wind_kph": closest_hour["wind_kph"],
                "chance_of_rain": closest_hour.get("chance_of_rain", 0),
            }
    except Exception as exc:
        logger.warning("Weather forecast failed for %s,%s on %s: %s", lat, lon, date_str, exc)
        return None
