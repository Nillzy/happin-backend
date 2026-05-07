"""Ticket business logic — generation, deletion, and retrieval."""

import secrets

from app.core.supabase import get_supabase_for_user


def create_tickets(
    event_id: str,
    person_id: str,
    token: str,
    ticket_option_id: str | None = None,
    quantity: int = 1,
) -> list[dict]:
    """Create one or more tickets, each with a unique qr_token."""
    supabase = get_supabase_for_user(token)

    payloads = []
    for _ in range(quantity):
        payload: dict = {
            "event_id": event_id,
            "person_id": person_id,
            "qr_token": secrets.token_urlsafe(32),
        }
        if ticket_option_id:
            payload["ticket_option_id"] = ticket_option_id
        payloads.append(payload)

    result = supabase.table("ticket").insert(payloads).execute()
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
            "ticket_id, qr_token, status, created_at, used_at, "
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
