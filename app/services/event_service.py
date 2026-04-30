"""Event-related business logic and Supabase queries."""

import secrets

from app.core.supabase import get_supabase, get_supabase_for_user


def _isoformat(value) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def get_public_events(limit: int = 50, offset: int = 0, person_id: str | None = None) -> list[dict]:
    supabase = get_supabase()

    response = (
        supabase.table("event")
        .select(
            "*, location(*), event_media(media_url), "
            "event_participation(event_participation_id, role, person_id)"
        )
        .eq("is_public", True)
        .eq("status", "published")
        .order("starts_at", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )

    events = response.data if response.data else []

    # Add is_host flag if person_id is provided
    if person_id:
        for event in events:
            participations = event.get("event_participation", [])
            event["is_host"] = any(
                p.get("person_id") == person_id and p.get("role") == "Host"
                for p in participations
            )
    else:
        for event in events:
            event["is_host"] = False

    return events


def get_event_by_id(event_id: str) -> dict | None:
    supabase = get_supabase()

    response = (
        supabase.table("event")
        .select(
            "*, location(*), event_media(media_url), ticket_option(*), "
            "event_participation(event_participation_id, role, person(person_id, supabase_user_id, first_name, last_name))"
        )
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )

    return response.data if response else None


def create_event(data: dict, person_id: str, token: str) -> dict:
    supabase = get_supabase_for_user(token)

    location_data = data.pop("location")
    location_insert = {k: v for k, v in location_data.items() if v is not None}
    location_resp = (
        supabase.table("location")
        .insert(location_insert)
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
        "is_free": data.get("is_free", True),
        "status": data.get("status", "published"),
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


def update_event(event_id: str, data: dict, person_id: str, token: str) -> dict | None:
    """Update an existing event. Only the host may update."""
    supabase = get_supabase_for_user(token)

    participation = (
        supabase.table("event_participation")
        .select("event_participation_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .eq("role", "Host")
        .maybe_single()
        .execute()
    )
    if not participation.data:
        return None

    location_data = data.pop("location", None)
    if location_data:
        event_row = (
            supabase.table("event")
            .select("location_id")
            .eq("event_id", event_id)
            .single()
            .execute()
        )
        location_id = event_row.data["location_id"]
        loc_patch = {k: v for k, v in location_data.items() if v is not None}
        if loc_patch:
            supabase.table("location").update(loc_patch).eq("location_id", location_id).execute()

    event_patch = {}
    for key, value in data.items():
        if value is not None:
            event_patch[key] = _isoformat(value) if hasattr(value, "isoformat") else value

    if event_patch:
        supabase.table("event").update(event_patch).eq("event_id", event_id).execute()

    if data.get("is_free") is True:
        supabase.table("ticket_option").delete().eq("event_id", event_id).execute()

    return get_event_by_id(event_id)


def is_user_host(event_id: str, person_id: str) -> bool:
    """Check if a person is the host of an event."""
    supabase = get_supabase()

    response = (
        supabase.table("event_participation")
        .select("event_participation_id, role")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .eq("role", "Host")
        .maybe_single()
        .execute()
    )

    return response is not None and response.data is not None


def get_event_participants(event_id: str) -> dict:
    """Get all participants for an event with counts by status."""
    supabase = get_supabase()

    response = (
        supabase.table("event_participation")
        .select("event_participation_id, status, created_at, person(person_id, first_name, last_name, phone_number)")
        .eq("event_id", event_id)
        .execute()
    )

    participants = response.data if response.data else []

    counts = {"accepted": 0, "declined": 0, "pending": 0}
    for p in participants:
        status = p.get("status", "").lower()
        if status == "accepted":
            counts["accepted"] += 1
        elif status == "declined":
            counts["declined"] += 1
        elif status == "pending":
            counts["pending"] += 1

    return {
        "participants": participants,
        "counts": counts,
    }


def remove_participants(event_id: str, participation_ids: list[str], token: str | None = None) -> int:
    """Remove participants from an event. Does not remove hosts."""
    if token:
        supabase = get_supabase_for_user(token)
    else:
        supabase = get_supabase()

    response = (
        supabase.table("event_participation")
        .delete()
        .eq("event_id", event_id)
        .in_("event_participation_id", participation_ids)
        .neq("role", "Host")
        .execute()
    )

    return len(response.data) if response.data else 0
