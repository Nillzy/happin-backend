"""Event-related business logic and Supabase queries."""

from app.core.supabase import get_supabase


def get_public_events(limit: int = 50, offset: int = 0) -> list[dict]:
    supabase = get_supabase()

    response = (
        supabase.table("event")
        .select(
            "*, location(*), event_media(media_url), "
            "event_participation(event_participation_id)"
        )
        .eq("is_public", True)
        .order("date", desc=False)
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

    return response.data
