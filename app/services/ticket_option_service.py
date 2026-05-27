"""Ticket option business logic — UPSERT sync for pricing categories."""

from app.core.supabase import get_supabase, get_supabase_for_user
from app.services import payment_service


def get_ticket_options(event_id: str) -> list[dict]:
    supabase = get_supabase()
    response = (
        supabase.table("ticket_option")
        .select("*")
        .eq("event_id", event_id)
        .order("sort_order")
        .execute()
    )
    return response.data


def sync_ticket_options(event_id: str, options: list[dict], token: str) -> list[dict]:
    """
    UPSERT sync: compare incoming options with existing ones.
    - Items with ticket_option_id → UPDATE
    - Items without ticket_option_id → INSERT
    - Existing IDs not in request → DELETE

    Synchronisiert anschließend `event.is_free` mit dem tatsächlichen Preis-Zustand:
    mindestens eine Option mit Preis > 0 ⇒ `is_free=False`, sonst `True`.
    """
    payment_service.require_stripe_for_paid_public_tickets(event_id, options)
    supabase = get_supabase_for_user(token)

    existing = (
        supabase.table("ticket_option")
        .select("ticket_option_id")
        .eq("event_id", event_id)
        .execute()
    )
    existing_ids = {row["ticket_option_id"] for row in existing.data}

    incoming_ids = set()
    for opt in options:
        if opt.get("ticket_option_id"):
            incoming_ids.add(opt["ticket_option_id"])

    ids_to_delete = existing_ids - incoming_ids
    if ids_to_delete:
        supabase.table("ticket_option").delete().in_(
            "ticket_option_id", list(ids_to_delete)
        ).execute()

    for opt in options:
        opt_id = opt.pop("ticket_option_id", None)
        row = {
            "event_id": event_id,
            "name": opt["name"],
            "description": opt.get("description"),
            "price": opt.get("price", 0.0),
            "quantity_limit": opt.get("quantity_limit"),
            "sort_order": opt.get("sort_order", 0),
        }

        if opt_id and opt_id in existing_ids:
            supabase.table("ticket_option").update(row).eq(
                "ticket_option_id", opt_id
            ).execute()
        else:
            supabase.table("ticket_option").insert(row).execute()

    result = get_ticket_options(event_id)
    _sync_event_is_free(supabase, event_id, result)
    return result


def _sync_event_is_free(supabase, event_id: str, options: list[dict]) -> None:
    has_paid = any(float(opt.get("price", 0) or 0) > 0 for opt in options)
    supabase.table("event").update({"is_free": not has_paid}).eq(
        "event_id", event_id
    ).execute()
