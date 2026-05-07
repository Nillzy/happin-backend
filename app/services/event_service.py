"""Event-related business logic and Supabase queries."""

import secrets
from datetime import datetime, timezone, UTC

from app.core.supabase import get_supabase, get_supabase_for_user, get_supabase_admin
from app.services import person_service
from app.services.geocoding_service import geocode_address


def _isoformat(value) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def get_public_events(limit: int = 50, offset: int = 0, person_id: str | None = None) -> tuple[list[dict], int]:
    """
    Get public events with pagination.
    Returns (events, total_count) tuple.
    """
    supabase = get_supabase()

    # Get total count (same filters as paginated query)
    count_response = (
        supabase.table("event")
        .select("event_id", count="exact")
        .eq("is_public", True)
        .eq("status", "published")
        .gte("starts_at", datetime.now(UTC).isoformat())
        .execute()
    )
    total_count = count_response.count if hasattr(count_response, 'count') else 0

    # Get paginated events
    response = (
        supabase.table("event")
        .select(
            "*, location(*), event_media(media_url), "
            "event_host(person_id), "
            "ticket(ticket_id)"
        )
        .eq("is_public", True)
        .eq("status", "published")
        .gte("starts_at", datetime.now(UTC).isoformat())
        .order("starts_at", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )

    events = response.data if response.data else []

    for event in events:
        if person_id:
            event["is_host"] = any(
                h.get("person_id") == person_id
                for h in event.get("event_host", [])
            )
        else:
            event["is_host"] = False

    return events, total_count

def get_public_events_count() -> int:
    supabase = get_supabase()

    response = (
        supabase.table("event")
        .select("*", count="exact")
        .eq("is_public", True)
        .eq("status", "published")
        .gte("starts_at", datetime.now(UTC).isoformat())
        .execute()
    )

    return response.count or 0


def get_event_by_id(event_id: str, supabase_user_id: str | None = None, token: str | None = None) -> dict | None:
    supabase = get_supabase_for_user(token) if token else get_supabase()

    response = (
        supabase.table("event")
        .select(
            "*, location(*), event_media(media_url), ticket_option(*), "
            "event_host(person(person_id, supabase_user_id, first_name, last_name)), "
            "event_participation(event_participation_id, status, person(person_id, supabase_user_id)), "
            "ticket(ticket_id)"
        )
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )

    if not response or not response.data:
        return None

    data = response.data

    if supabase_user_id:
        participations = data.get("event_participation") or []
        my_participation = next(
            (p for p in participations
             if p.get("person", {}).get("supabase_user_id") == supabase_user_id),
            None,
        )
        data["my_rsvp_status"] = my_participation["status"] if my_participation else None

        hosts = data.get("event_host") or []
        data["is_host"] = any(
            h.get("person", {}).get("supabase_user_id") == supabase_user_id
            for h in hosts
        )
    else:
        data["my_rsvp_status"] = None
        data["is_host"] = False

    return data


def create_event(data: dict, person_id: str, token: str, supabase_user_id: str | None = None) -> dict:
    supabase = get_supabase_for_user(token)

    location_data = data.pop("location")
    location_insert = {k: v for k, v in location_data.items() if v is not None}
    location_resp = (
        supabase.table("location")
        .insert(location_insert)
        .execute()
    )
    location_id = location_resp.data[0]["location_id"]

    coords = geocode_address(
        street=location_data.get("street"),
        house_number=location_data.get("house_number"),
        postal_code=location_data.get("postal_code"),
        city=location_data.get("city"),
        country=location_data.get("country"),
    )
    if coords:
        supabase.table("location").update({
            "latitude": coords[0],
            "longitude": coords[1],
        }).eq("location_id", location_id).execute()

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
    if data.get("gradient_id") is not None:
        event_payload["gradient_id"] = data["gradient_id"]

    event_resp = (
        supabase.table("event")
        .insert(event_payload)
        .execute()
    )
    event_id = event_resp.data[0]["event_id"]

    supabase.table("event_host").insert({
        "person_id": person_id,
        "event_id": event_id,
    }).execute()

    image_url = data.get("image_url")
    if image_url:
        supabase.table("event_media").insert({
            "event_id": event_id,
            "media_url": image_url,
        }).execute()

    return get_event_by_id(event_id, supabase_user_id=supabase_user_id, token=token)


def update_event(event_id: str, data: dict, person_id: str, token: str, supabase_user_id: str | None = None) -> dict | None:
    """Update an existing event. Only the host may update."""
    supabase = get_supabase_for_user(token)

    host_entry = (
        supabase.table("event_host")
        .select("event_host_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .maybe_single()
        .execute()
    )
    if not host_entry.data:
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

    has_image_url_field = "image_url" in data
    image_url = data.pop("image_url", None)
    if has_image_url_field:
        existing_media = (
            supabase.table("event_media")
            .select("media_id")
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )
        if image_url:
            if existing_media.data:
                supabase.table("event_media").update({
                    "media_url": image_url,
                }).eq("media_id", existing_media.data[0]["media_id"]).execute()
            else:
                supabase.table("event_media").insert({
                    "event_id": event_id,
                    "media_url": image_url,
                }).execute()
        elif existing_media.data:
            supabase.table("event_media").delete().eq(
                "media_id", existing_media.data[0]["media_id"]
            ).execute()

    event_patch = {}
    for key, value in data.items():
        event_patch[key] = _isoformat(value) if hasattr(value, "isoformat") else value

    if event_patch:
        supabase.table("event").update(event_patch).eq("event_id", event_id).execute()

    if data.get("is_free") is True:
        supabase.table("ticket_option").delete().eq("event_id", event_id).execute()

    return get_event_by_id(event_id, supabase_user_id=supabase_user_id, token=token)


def rsvp_event(event_id: str, supabase_user_id: str, email: str | None, status: str, token: str) -> dict:
    """Create or update a guest RSVP for an event."""
    supabase = get_supabase_for_user(token)

    person = person_service.get_or_create_person(supabase_user_id, email, token)
    person_id = person["person_id"]

    event_row = (
        supabase.table("event")
        .select("starts_at, is_public")
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )
    if not event_row.data:
        raise ValueError("event_not_found")

    starts_at_str = event_row.data["starts_at"]
    starts_at = datetime.fromisoformat(starts_at_str.replace("Z", "+00:00"))
    if starts_at <= datetime.now(timezone.utc):
        raise ValueError("event_in_past")

    if event_row.data["is_public"] and status == "Pending":
        raise ValueError("public_event_accepted_only")

    result = supabase.rpc("rsvp_to_event", {
        "p_event_id": event_id,
        "p_person_id": person_id,
        "p_status": status,
    }).execute()

    rpc_data = result.data
    if isinstance(rpc_data, dict) and rpc_data.get("error"):
        raise ValueError(rpc_data["error"])

    participation = (
        supabase.table("event_participation")
        .select("event_participation_id, event_id, person_id, status")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .single()
        .execute()
    )
    return participation.data


def is_user_host(event_id: str, person_id: str) -> bool:
    """Check if a person is the host of an event."""
    supabase = get_supabase()

    response = (
        supabase.table("event_host")
        .select("event_host_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
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
    """Remove participants from an event. Does not remove hosts.
    Requires a user token — RLS policy ensures only hosts can delete."""
    if token:
        client = get_supabase_for_user(token)
    else:
        client = get_supabase()

    response = (
        client.table("event_participation")
        .delete()
        .eq("event_id", event_id)
        .in_("event_participation_id", participation_ids)
        .execute()
    )

    return len(response.data) if response.data else 0
