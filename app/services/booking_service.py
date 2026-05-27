"""Shared validation for ticket booking (free RSVP, direct booking, paid checkout)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

# Stripe Checkout sessions expire after 30 min; allow a small buffer.
PENDING_ORDER_TTL_MINUTES = 35


class SupabaseClient(Protocol):
    def table(self, name: str) -> Any: ...


def get_ticket_option(
    supabase: SupabaseClient,
    ticket_option_id: str,
    *,
    event_id: str | None = None,
) -> dict:
    """Load ticket option; optionally verify it belongs to event_id."""
    row = (
        supabase.table("ticket_option")
        .select("ticket_option_id, event_id, name, price, quantity_limit")
        .eq("ticket_option_id", ticket_option_id)
        .single()
        .execute()
    )
    data = row.data
    if event_id and data.get("event_id") != event_id:
        raise ValueError("ticket_option_wrong_event")
    return data


def count_event_tickets(supabase: SupabaseClient, event_id: str) -> int:
    resp = (
        supabase.table("ticket")
        .select("ticket_id", count="exact")
        .eq("event_id", event_id)
        .execute()
    )
    return resp.count or 0


def count_pending_order_quantity(supabase: SupabaseClient, event_id: str) -> int:
    rows = (
        supabase.table("ticket_order")
        .select("quantity")
        .eq("event_id", event_id)
        .eq("status", "pending")
        .execute()
    )
    return sum(r["quantity"] for r in (rows.data or []))


def count_user_tickets(supabase: SupabaseClient, event_id: str, person_id: str) -> int:
    resp = (
        supabase.table("ticket")
        .select("ticket_id", count="exact")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .execute()
    )
    return resp.count or 0


def count_user_pending_order_quantity(
    supabase: SupabaseClient, event_id: str, person_id: str
) -> int:
    rows = (
        supabase.table("ticket_order")
        .select("quantity")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .eq("status", "pending")
        .execute()
    )
    return sum(r["quantity"] for r in (rows.data or []))


def get_max_tickets_per_person(supabase: SupabaseClient, event_id: str) -> int | None:
    row = (
        supabase.table("event")
        .select("max_tickets_per_person, max_capacity")
        .eq("event_id", event_id)
        .single()
        .execute()
    )
    value = (row.data or {}).get("max_tickets_per_person")
    if value is None:
        return None
    return int(value)


def user_has_paid_purchase(
    supabase: SupabaseClient, event_id: str, person_id: str
) -> bool:
    """True if user has a paid/refunded order or tickets linked to a paid order."""
    paid_order = (
        supabase.table("ticket_order")
        .select("ticket_order_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .in_("status", ["paid", "refunded"])
        .limit(1)
        .execute()
    )
    if paid_order.data:
        return True

    linked = (
        supabase.table("ticket")
        .select("ticket_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .not_.is_("ticket_order_id", "null")
        .limit(1)
        .execute()
    )
    return bool(linked.data)


def expire_stale_pending_orders(
    supabase: SupabaseClient, event_id: str, person_id: str
) -> None:
    """Expire abandoned pending orders (no session or past checkout TTL)."""
    rows = (
        supabase.table("ticket_order")
        .select("ticket_order_id, stripe_checkout_session_id, created_at")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .eq("status", "pending")
        .execute()
    )
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=PENDING_ORDER_TTL_MINUTES)
    for row in rows.data or []:
        created_raw = row.get("created_at")
        created_at = None
        if created_raw:
            created_at = datetime.fromisoformat(
                str(created_raw).replace("Z", "+00:00")
            )
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        stale = not row.get("stripe_checkout_session_id")
        if created_at and created_at < cutoff:
            stale = True
        if stale:
            supabase.table("ticket_order").update({"status": "expired"}).eq(
                "ticket_order_id", row["ticket_order_id"]
            ).eq("status", "pending").execute()


def clear_pending_checkouts(
    supabase: SupabaseClient, event_id: str, person_id: str
) -> None:
    """
    Expire abandoned pending checkouts only.
    Keeps orders linked to an active Stripe Checkout session intact so webhooks can fulfill them.
    """
    expire_stale_pending_orders(supabase, event_id, person_id)
    supabase.table("ticket_order").update({"status": "expired"}).eq(
        "event_id", event_id
    ).eq("person_id", person_id).eq("status", "pending").is_(
        "stripe_checkout_session_id", "null"
    ).execute()


def user_has_pending_checkout(
    supabase: SupabaseClient, event_id: str, person_id: str
) -> bool:
    expire_stale_pending_orders(supabase, event_id, person_id)
    row = (
        supabase.table("ticket_order")
        .select("ticket_order_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .eq("status", "pending")
        .limit(1)
        .execute()
    )
    return bool(row.data)


def validate_booking(
    supabase: SupabaseClient,
    *,
    event_id: str,
    person_id: str,
    quantity: int,
    ticket_option_id: str | None = None,
    allow_free_only: bool = False,
    is_checkout: bool = False,
) -> dict | None:
    """
    Validate capacity, per-person limits, and ticket option rules.
    Returns ticket option row when ticket_option_id is set.
    Raises ValueError with stable error codes.
    """
    if is_checkout:
        expire_stale_pending_orders(supabase, event_id, person_id)

    event_row = (
        supabase.table("event")
        .select("max_capacity")
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )
    if not getattr(event_row, "data", None):
        raise ValueError("event_not_found")

    opt_data = None
    if ticket_option_id:
        opt_data = get_ticket_option(supabase, ticket_option_id, event_id=event_id)
        unit_price_cents = int(float(opt_data["price"]) * 100)
        if allow_free_only and unit_price_cents > 0:
            raise ValueError("payment_required")
        if is_checkout and unit_price_cents <= 0:
            raise ValueError("ticket_option_free")
        qty_limit = opt_data.get("quantity_limit")
        if qty_limit is not None and qty_limit < quantity:
            raise ValueError("ticket_option_sold_out")
    elif is_checkout:
        raise ValueError("ticket_option_required")

    max_cap = (event_row.data or {}).get("max_capacity")
    if max_cap is not None:
        current = count_event_tickets(supabase, event_id)
        pending = count_pending_order_quantity(supabase, event_id)
        notified_resp = (
            supabase.table("event_waitlist")
            .select("waitlist_id", count="exact")
            .eq("event_id", event_id)
            .eq("status", "notified")
            .execute()
        )
        notified = notified_resp.count or 0
        if current + pending + notified + quantity > int(max_cap):
            raise ValueError("event_full")

    max_per_person = get_max_tickets_per_person(supabase, event_id)
    user_tickets = count_user_tickets(supabase, event_id, person_id)
    user_pending = count_user_pending_order_quantity(supabase, event_id, person_id)
    if max_per_person is not None and user_tickets + user_pending + quantity > max_per_person:
        raise ValueError("max_tickets_exceeded")

    if is_checkout:
        if user_has_pending_checkout(supabase, event_id, person_id):
            raise ValueError("checkout_pending")

    return opt_data
