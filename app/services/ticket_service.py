"""Ticket business logic — generation, deletion, and retrieval."""

from app.core.supabase import get_supabase_for_user
from app.core.ticket_token import generate_ticket_token, verify_ticket_token


def create_tickets(
    event_id: str,
    person_id: str,
    token: str,
    ticket_option_id: str | None = None,
    quantity: int = 1,
    guest_name: str | None = None,
    guest_names: list[str] | None = None,
    ticket_option_name: str | None = None,
) -> list[dict]:
    """Create one or more tickets with HMAC-signed qr_tokens."""
    supabase = get_supabase_for_user(token)

    if not guest_name:
        person = supabase.table("person").select("first_name, last_name").eq("person_id", person_id).single().execute()
        p = person.data or {}
        parts = [p.get("first_name", ""), p.get("last_name", "")]
        guest_name = " ".join(x for x in parts if x).strip() or "Gast"

    if ticket_option_id and not ticket_option_name:
        opt = supabase.table("ticket_option").select("name").eq("ticket_option_id", ticket_option_id).single().execute()
        ticket_option_name = (opt.data or {}).get("name")

    existing_resp = (
        supabase.table("ticket")
        .select("ticket_id", count="exact")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .order("created_at")
        .execute()
    )
    existing_count = existing_resp.count or 0

    # When names are provided, patch existing tickets so a re-RSVP updates names too.
    if guest_names and existing_count > 0:
        existing_ids = [r["ticket_id"] for r in (existing_resp.data or [])]
        for i, tid in enumerate(existing_ids):
            name = (guest_names[i].strip() if i < len(guest_names) else None) or guest_name or "Gast"
            qr_token = generate_ticket_token(event_id, name, i + 1, ticket_option_name)
            supabase.table("ticket").update({"guest_name": name, "qr_token": qr_token}).eq("ticket_id", tid).execute()

    if existing_count >= quantity:
        return []

    payloads = []
    for i in range(quantity - existing_count):
        ticket_nr = existing_count + i + 1
        name_idx = existing_count + i
        name = (guest_names[name_idx] if guest_names and name_idx < len(guest_names) else guest_name) or "Gast"
        qr_token = generate_ticket_token(event_id, name, ticket_nr, ticket_option_name)
        payload: dict = {
            "event_id": event_id,
            "person_id": person_id,
            "qr_token": qr_token,
            "guest_name": name,
        }
        if ticket_option_id:
            payload["ticket_option_id"] = ticket_option_id
        payloads.append(payload)

    result = supabase.table("ticket").insert(payloads).execute()

    if ticket_option_id:
        opt_row = supabase.table("ticket_option").select("quantity_limit").eq("ticket_option_id", ticket_option_id).single().execute()
        current_limit = (opt_row.data or {}).get("quantity_limit")
        if current_limit is not None:
            supabase.table("ticket_option").update({"quantity_limit": max(0, current_limit - quantity)}).eq("ticket_option_id", ticket_option_id).execute()

    return result.data


def delete_tickets_for_event(event_id: str, person_id: str, token: str) -> None:
    """Delete ALL tickets for a person at a given event (used on RSVP decline)."""
    supabase = get_supabase_for_user(token)
    supabase.table("ticket").delete().eq("event_id", event_id).eq("person_id", person_id).execute()


def delete_ticket_by_id(ticket_id: str, token: str) -> None:
    """Delete a single ticket by its ID."""
    supabase = get_supabase_for_user(token)
    supabase.table("ticket").delete().eq("ticket_id", ticket_id).execute()


def get_tickets_for_person(person_id: str, token: str) -> dict:
    """Get all tickets for a person with event and ticket option details."""
    supabase = get_supabase_for_user(token)

    response = (
        supabase.table("ticket")
        .select(
            "ticket_id, qr_token, status, created_at, used_at, guest_name, "
            "event(event_id, title, starts_at, location(city)), "
            "ticket_option(ticket_option_id, name, price)"
        )
        .eq("person_id", person_id)
        .order("created_at", desc=True)
        .execute()
    )

    rows = response.data or []
    tickets = []
    for row in rows:
        event = row.get("event") or {}
        option = row.get("ticket_option") or {}
        location = event.get("location") or {}
        tickets.append({
            "ticket_id": row["ticket_id"],
            "qr_token": row["qr_token"],
            "guest_name": row.get("guest_name"),
            "event_id": event.get("event_id", ""),
            "event_title": event.get("title", ""),
            "starts_at": event.get("starts_at"),
            "city": location.get("city"),
            "ticket_option_name": option.get("name", "Standard"),
            "price": float(option.get("price", 0.0)),
            "currency": "EUR",
            "status": row.get("status", "active"),
            "created_at": row.get("created_at"),
            "used_at": row.get("used_at"),
        })

    return {"tickets": tickets, "total": len(tickets)}


def get_tickets_for_event(event_id: str, person_id: str, token: str) -> list[dict]:
    """Get all tickets for a person at a specific event."""
    supabase = get_supabase_for_user(token)
    response = (
        supabase.table("ticket")
        .select("ticket_id, qr_token, guest_name, status")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .order("created_at")
        .execute()
    )
    return response.data or []


def validate_ticket(event_id: str, qr_token: str, token: str) -> dict:
    """Validate and mark a ticket as used. Returns scan result dict."""
    from datetime import datetime, timezone

    payload = verify_ticket_token(qr_token, event_id)
    if not payload:
        return {"valid": False, "reason": "not_found"}

    supabase = get_supabase_for_user(token)

    row = (
        supabase.table("ticket")
        .select("ticket_id, status, used_at")
        .eq("event_id", event_id)
        .eq("qr_token", qr_token)
        .maybe_single()
        .execute()
    )

    if not row or not row.data:
        return {"valid": False, "reason": "not_found"}

    ticket = row.data
    guest_name = payload.get("name")
    ticket_number = payload.get("nr")
    option_name = payload.get("opt")

    if ticket["status"] == "used":
        return {
            "valid": False,
            "reason": "already_used",
            "guest_name": guest_name,
            "used_at": ticket.get("used_at"),
            "ticket_number": ticket_number,
            "option_name": option_name,
        }

    now = datetime.now(timezone.utc).isoformat()
    update_result = (
        supabase.table("ticket")
        .update({"status": "used", "used_at": now})
        .eq("ticket_id", ticket["ticket_id"])
        .execute()
    )

    if not update_result.data:
        raise PermissionError("Could not mark ticket as used — UPDATE policy missing?")

    return {
        "valid": True,
        "guest_name": guest_name,
        "used_at": now,
        "ticket_number": ticket_number,
        "option_name": option_name,
    }
