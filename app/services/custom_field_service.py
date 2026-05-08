"""Custom field business logic — UPSERT sync for event form definitions + guest responses."""

from app.core.supabase import get_supabase, get_supabase_for_user


def get_custom_fields(event_id: str) -> list[dict]:
    supabase = get_supabase()
    response = (
        supabase.table("custom_field")
        .select("*")
        .eq("event_id", event_id)
        .order("sort_order")
        .execute()
    )
    return response.data


def sync_custom_fields(event_id: str, fields: list[dict], token: str) -> list[dict]:
    """
    UPSERT sync: compare incoming fields with existing ones.
    - Items with custom_field_id → UPDATE
    - Items without custom_field_id → INSERT
    - Existing IDs not in request → DELETE
    """
    supabase = get_supabase_for_user(token)

    existing = (
        supabase.table("custom_field")
        .select("custom_field_id")
        .eq("event_id", event_id)
        .execute()
    )
    existing_ids = {row["custom_field_id"] for row in existing.data}

    incoming_ids = set()
    for field in fields:
        if field.get("custom_field_id"):
            incoming_ids.add(field["custom_field_id"])

    ids_to_delete = existing_ids - incoming_ids
    if ids_to_delete:
        supabase.table("custom_field").delete().in_(
            "custom_field_id", list(ids_to_delete)
        ).execute()

    for field in fields:
        field_id = field.pop("custom_field_id", None)
        row = {
            "event_id": event_id,
            "label": field["label"],
            "field_type": field["field_type"],
            "is_required": field.get("is_required", False),
            "options": field.get("options"),
            "sort_order": field.get("sort_order", 0),
        }

        if field_id and field_id in existing_ids:
            supabase.table("custom_field").update(row).eq(
                "custom_field_id", field_id
            ).execute()
        else:
            supabase.table("custom_field").insert(row).execute()

    return get_custom_fields(event_id)


def submit_responses(
    event_participation_id: str, responses: list[dict], token: str
) -> list[dict]:
    """UPSERT guest responses for a participation (one per custom_field)."""
    supabase = get_supabase_for_user(token)

    for resp in responses:
        row = {
            "event_participation_id": event_participation_id,
            "custom_field_id": resp["custom_field_id"],
            "value": resp["value"],
            "updated_at": "now()",
        }
        supabase.table("custom_field_response").upsert(
            row, on_conflict="event_participation_id,custom_field_id"
        ).execute()

    return get_responses_for_participation(event_participation_id, token)


def get_responses_for_participation(
    event_participation_id: str, token: str
) -> list[dict]:
    supabase = get_supabase_for_user(token)
    response = (
        supabase.table("custom_field_response")
        .select("*")
        .eq("event_participation_id", event_participation_id)
        .execute()
    )
    return response.data


def get_all_responses_for_event(event_id: str, token: str) -> list[dict]:
    """Fetch all custom field responses for an event (host view)."""
    supabase = get_supabase_for_user(token)
    response = (
        supabase.table("custom_field_response")
        .select("*, event_participation!inner(event_id, person_id)")
        .eq("event_participation.event_id", event_id)
        .execute()
    )
    return response.data
