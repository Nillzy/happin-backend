"""Calendar export service for generating ICS files."""

from datetime import datetime, timedelta, UTC
from icalendar import Calendar, Event, vText
from app.core.supabase import get_supabase, get_supabase_for_user


def _format_location(location: dict | None) -> str | None:
    """Format location dict into a single address string."""
    if not location:
        return None

    parts = []
    if location.get("street"):
        street = location["street"]
        if location.get("house_number"):
            street += f" {location['house_number']}"
        parts.append(street)

    if location.get("postal_code") or location.get("city"):
        city_part = " ".join(
            filter(None, [location.get("postal_code"), location.get("city")])
        )
        if city_part:
            parts.append(city_part)

    if location.get("country"):
        parts.append(location["country"])

    return ", ".join(parts) if parts else None


def get_event_for_calendar(event_id: str, token: str | None = None) -> dict | None:
    """Fetch event data needed for calendar export."""
    supabase = get_supabase_for_user(token) if token else get_supabase()

    response = (
        supabase.table("event")
        .select("event_id, title, description, starts_at, ends_at, location(*)")
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )

    if not response or not response.data:
        return None

    return response.data


def generate_ics(event_id: str, token: str | None = None) -> bytes | None:
    """
    Generate an ICS file for an event.

    Args:
        event_id: The UUID of the event
        token: Optional JWT token for accessing private events

    Returns:
        ICS file content as bytes, or None if event not found
    """
    event_data = get_event_for_calendar(event_id, token)
    if not event_data:
        return None

    cal = Calendar()
    cal.add("prodid", "-//Happin//Event Calendar//DE")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")

    event = Event()

    event.add("uid", f"{event_id}@happin.app")
    event.add("summary", event_data["title"])

    starts_at_str = event_data["starts_at"]
    starts_at = datetime.fromisoformat(starts_at_str.replace("Z", "+00:00"))
    event.add("dtstart", starts_at)

    if event_data.get("ends_at"):
        ends_at_str = event_data["ends_at"]
        ends_at = datetime.fromisoformat(ends_at_str.replace("Z", "+00:00"))
        event.add("dtend", ends_at)
    else:
        event.add("dtend", starts_at + timedelta(hours=2))

    if event_data.get("description"):
        event.add("description", event_data["description"])

    location_str = _format_location(event_data.get("location"))
    if location_str:
        event["location"] = vText(location_str)

    event.add("dtstamp", datetime.now(UTC))

    cal.add_component(event)

    return cal.to_ical()
