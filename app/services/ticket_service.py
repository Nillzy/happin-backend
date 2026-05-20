"""Ticket business logic — generation, deletion, and retrieval."""

from __future__ import annotations

from app.core.supabase import get_supabase_for_user
from app.core.ticket_token import generate_ticket_token, verify_ticket_token


def _resolve_guest_name(supabase, person_id: str, guest_name: str | None) -> str:
    if guest_name:
        return guest_name
    person = (
        supabase.table("person")
        .select("first_name, last_name")
        .eq("person_id", person_id)
        .single()
        .execute()
    )
    p = person.data or {}
    parts = [p.get("first_name", ""), p.get("last_name", "")]
    return " ".join(x for x in parts if x).strip() or "Gast"


def _resolve_option_name(supabase, ticket_option_id: str | None, ticket_option_name: str | None) -> str | None:
    if not ticket_option_id or ticket_option_name:
        return ticket_option_name
    opt = (
        supabase.table("ticket_option")
        .select("name")
        .eq("ticket_option_id", ticket_option_id)
        .single()
        .execute()
    )
    return (opt.data or {}).get("name")


def _decrement_option_limit(supabase, ticket_option_id: str, amount: int) -> None:
    if amount <= 0 or not ticket_option_id:
        return
    opt_row = (
        supabase.table("ticket_option")
        .select("quantity_limit")
        .eq("ticket_option_id", ticket_option_id)
        .single()
        .execute()
    )
    current_limit = (opt_row.data or {}).get("quantity_limit")
    if current_limit is not None:
        supabase.table("ticket_option").update({
            "quantity_limit": max(0, current_limit - amount),
        }).eq("ticket_option_id", ticket_option_id).execute()


def ensure_participation_accepted(supabase, event_id: str, person_id: str) -> None:
    """Set RSVP to Accepted (insert or update)."""
    existing = (
        supabase.table("event_participation")
        .select("event_participation_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .maybe_single()
        .execute()
    )
    ep_data = getattr(existing, "data", None) if existing else None
    if ep_data:
        supabase.table("event_participation").update({"status": "Accepted"}).eq(
            "event_participation_id", ep_data["event_participation_id"]
        ).execute()
    else:
        supabase.table("event_participation").insert({
            "event_id": event_id,
            "person_id": person_id,
            "status": "Accepted",
        }).execute()


def create_tickets_for_order(
    supabase,
    *,
    ticket_order_id: str,
    event_id: str,
    person_id: str,
    ticket_option_id: str | None,
    quantity: int,
    guest_name: str | None = None,
    guest_names: list[str] | None = None,
) -> list[dict]:
    """Create tickets for a paid order (admin client). Idempotent per order_id."""
    order_ticket_count = (
        supabase.table("ticket")
        .select("ticket_id", count="exact")
        .eq("ticket_order_id", ticket_order_id)
        .execute()
    )
    already_for_order = order_ticket_count.count or 0
    if already_for_order >= quantity:
        existing = (
            supabase.table("ticket")
            .select("ticket_id")
            .eq("ticket_order_id", ticket_order_id)
            .execute()
        )
        return existing.data or []

    to_create = quantity - already_for_order

    guest_name = _resolve_guest_name(supabase, person_id, guest_name)
    ticket_option_name = _resolve_option_name(supabase, ticket_option_id, None)

    existing_resp = (
        supabase.table("ticket")
        .select("ticket_id", count="exact")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .execute()
    )
    existing_count = existing_resp.count or 0

    if not guest_names and quantity > 1:
        base = guest_name.rstrip()
        guest_names = [f"{base} {i + 1}" for i in range(quantity)]

    payloads = []
    for i in range(to_create):
        ticket_nr = existing_count + i + 1
        name = (
            guest_names[already_for_order + i].strip()
            if guest_names and (already_for_order + i) < len(guest_names)
            else guest_name
        ) or "Gast"
        qr_token = generate_ticket_token(event_id, name, ticket_nr, ticket_option_name)
        payload: dict = {
            "event_id": event_id,
            "person_id": person_id,
            "qr_token": qr_token,
            "guest_name": name,
            "ticket_order_id": ticket_order_id,
        }
        if ticket_option_id:
            payload["ticket_option_id"] = ticket_option_id
        payloads.append(payload)

    result = supabase.table("ticket").insert(payloads).execute()
    _decrement_option_limit(supabase, ticket_option_id, len(payloads))
    ensure_participation_accepted(supabase, event_id, person_id)
    return result.data or []


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
    """Create one or more free/RSVP tickets with HMAC-signed qr_tokens (user RLS)."""
    supabase = get_supabase_for_user(token)
    guest_name = _resolve_guest_name(supabase, person_id, guest_name)
    ticket_option_name = _resolve_option_name(supabase, ticket_option_id, ticket_option_name)

    existing_resp = (
        supabase.table("ticket")
        .select("ticket_id", count="exact")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .order("created_at")
        .execute()
    )
    existing_count = existing_resp.count or 0
    existing_rows = existing_resp.data or []

    if guest_names and existing_count > 0:
        for i, row in enumerate(existing_rows):
            tid = row["ticket_id"]
            name = (guest_names[i].strip() if i < len(guest_names) else None) or guest_name or "Gast"
            qr_token = generate_ticket_token(event_id, name, i + 1, ticket_option_name)
            supabase.table("ticket").update({
                "guest_name": name,
                "qr_token": qr_token,
            }).eq("ticket_id", tid).execute()

    if existing_count >= quantity:
        return []

    payloads = []
    for i in range(quantity - existing_count):
        ticket_nr = existing_count + i + 1
        name_idx = existing_count + i
        name = (
            guest_names[name_idx]
            if guest_names and name_idx < len(guest_names)
            else guest_name
        ) or "Gast"
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

    if not payloads:
        return []

    result = supabase.table("ticket").insert(payloads).execute()
    _decrement_option_limit(supabase, ticket_option_id, len(payloads))
    return result.data or []


def delete_tickets_for_event(event_id: str, person_id: str, token: str) -> None:
    """Delete free RSVP tickets only (not paid / order-linked tickets)."""
    supabase = get_supabase_for_user(token)
    supabase.table("ticket").delete().eq("event_id", event_id).eq(
        "person_id", person_id
    ).is_("ticket_order_id", "null").execute()


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
        qr_token = row["qr_token"]
        token_payload = verify_ticket_token(qr_token, event.get("event_id", ""))
        ticket_number = token_payload.get("nr") if token_payload else None
        tickets.append({
            "ticket_id": row["ticket_id"],
            "qr_token": qr_token,
            "guest_name": row.get("guest_name"),
            "ticket_number": ticket_number,
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

    tickets.sort(key=lambda t: t["ticket_number"] or 0)
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
