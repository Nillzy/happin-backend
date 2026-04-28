"""Event-related business logic and Supabase queries."""

import secrets

from app.core.supabase import get_supabase, get_supabase_for_user


def _isoformat(value) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def get_public_events(limit: int = 50, offset: int = 0) -> list[dict]:
    supabase = get_supabase()

    response = (
        supabase.table("event")
        .select(
            "*, location(*), event_media(media_url), "
            "event_participation(event_participation_id)"
        )
        .eq("is_public", True)
        .order("starts_at", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )

    return response.data


def get_event_by_id(event_id: int) -> dict | None:
    supabase = get_supabase()

    response = (
        supabase.table("event")
        .select(
            "*, location(*), event_media(media_url), "
            "event_participation(event_participation_id, role, person(first_name, last_name))"
        )
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )

    return response.data if response else None


def create_event(data: dict, person_id: int, token: str) -> dict:
    supabase = get_supabase_for_user(token)

    location_data = data.pop("location")
    location_resp = (
        supabase.table("location")
        .insert(location_data)
        .execute()
    )
    location_id = location_resp.data[0]["location_id"]

    invitation_link = secrets.token_urlsafe(16)

    event_payload = {
        "title": data["title"],
        "starts_at": _isoformat(data["starts_at"]),
        "description": data.get("description"),
        "category": data.get("category"),
        "max_capacity": data.get("max_capacity"),
        "is_public": data["is_public"],
        "location_id": location_id,
        "invitation_link": invitation_link,
    }
    if data.get("ends_at"):
        event_payload["ends_at"] = _isoformat(data["ends_at"])

    event_resp = (
        supabase.table("event")
        .insert(event_payload)
        .execute()
    )
    event_id = event_resp.data[0]["event_id"]

    supabase.table("event_participation").insert({
        "person_id": person_id,
        "event_id": event_id,
        "role": "Host",
        "status": "Accepted",
    }).execute()

    return get_event_by_id(event_id)
