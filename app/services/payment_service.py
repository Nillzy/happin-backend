"""Payment business logic — checkout, fulfillment, payouts."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.adapters import stripe_payment
from app.core.config import settings
from app.core.supabase import get_supabase_admin as get_supabase
from app.services import ticket_service, event_service

logger = logging.getLogger(__name__)


def calculate_application_fee(amount_cents: int) -> int:
    """Calculate the platform application fee from the total amount."""
    return round(amount_cents * settings.PLATFORM_FEE_BPS / 10000)


def get_host_stripe_account(event_id: str) -> dict | None:
    """Get the Stripe Connect account for the event's payout recipient."""
    supabase = get_supabase()

    event_row = (
        supabase.table("event")
        .select("payout_person_id")
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )
    payout_person_id = (event_row.data or {}).get("payout_person_id")

    if not payout_person_id:
        # Fallback: earliest host
        host_row = (
            supabase.table("event_host")
            .select("person_id")
            .eq("event_id", event_id)
            .order("created_at")
            .limit(1)
            .maybe_single()
            .execute()
        )
        if not host_row.data:
            return None
        payout_person_id = host_row.data["person_id"]

    person = (
        supabase.table("person")
        .select("person_id, stripe_connect_account_id, stripe_connect_charges_enabled")
        .eq("person_id", payout_person_id)
        .maybe_single()
        .execute()
    )
    return person.data


def create_checkout_session(
    *,
    event_id: str,
    person_id: str,
    ticket_option_id: str,
    quantity: int,
    person_email: str | None = None,
) -> dict:
    """Create a Stripe Checkout Session and a pending ticket_order."""
    supabase = get_supabase()

    # Load ticket option
    option = (
        supabase.table("ticket_option")
        .select("name, price, quantity_limit")
        .eq("ticket_option_id", ticket_option_id)
        .single()
        .execute()
    )
    opt_data = option.data
    unit_price_cents = int(float(opt_data["price"]) * 100)

    if unit_price_cents <= 0:
        raise ValueError("ticket_option_free")

    # Capacity check: tickets + pending orders
    event_row = (
        supabase.table("event")
        .select("max_capacity, title")
        .eq("event_id", event_id)
        .single()
        .execute()
    )
    max_cap = event_row.data.get("max_capacity")
    if max_cap is not None:
        current_tickets = (
            supabase.table("ticket")
            .select("ticket_id", count="exact")
            .eq("event_id", event_id)
            .execute()
        ).count or 0
        pending_orders = (
            supabase.table("ticket_order")
            .select("quantity")
            .eq("event_id", event_id)
            .eq("status", "pending")
            .execute()
        )
        pending_qty = sum(r["quantity"] for r in (pending_orders.data or []))
        if current_tickets + pending_qty + quantity > int(max_cap):
            raise ValueError("event_full")

    # Check ticket option quantity limit
    qty_limit = opt_data.get("quantity_limit")
    if qty_limit is not None and qty_limit < quantity:
        raise ValueError("ticket_option_sold_out")

    # Get host Stripe account
    host_info = get_host_stripe_account(event_id)
    if not host_info or not host_info.get("stripe_connect_account_id"):
        raise ValueError("host_not_onboarded")
    if not host_info.get("stripe_connect_charges_enabled"):
        raise ValueError("host_charges_not_enabled")

    destination_account = host_info["stripe_connect_account_id"]
    amount_total_cents = unit_price_cents * quantity
    fee_cents = calculate_application_fee(amount_total_cents)

    # Create pending order
    order_result = (
        supabase.table("ticket_order")
        .insert({
            "event_id": event_id,
            "person_id": person_id,
            "ticket_option_id": ticket_option_id,
            "quantity": quantity,
            "amount_total_cents": amount_total_cents,
            "application_fee_cents": fee_cents,
            "status": "pending",
        })
        .execute()
    )
    order = order_result.data[0]
    order_id = order["ticket_order_id"]

    # Build success/cancel URLs
    success_url = settings.STRIPE_CHECKOUT_SUCCESS_URL
    if "{CHECKOUT_SESSION_ID}" not in success_url:
        separator = "&" if "?" in success_url else "?"
        success_url += f"{separator}session_id={{CHECKOUT_SESSION_ID}}"
    # Append event_id so the frontend can navigate to the correct ticket
    separator = "&" if "?" in success_url else "?"
    success_url += f"{separator}event_id={event_id}"

    cancel_url = settings.STRIPE_CHECKOUT_CANCEL_URL or success_url

    event_title = event_row.data.get("title", "Event")
    product_name = f"{event_title} – {opt_data['name']}"

    session = stripe_payment.create_checkout_session(
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {"name": product_name},
                "unit_amount": unit_price_cents,
            },
            "quantity": quantity,
        }],
        destination_account_id=destination_account,
        application_fee_amount=fee_cents,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "ticket_order_id": order_id,
            "event_id": event_id,
            "person_id": person_id,
        },
        customer_email=person_email,
        idempotency_key=order_id,
    )

    # Store checkout session ID on order
    supabase.table("ticket_order").update({
        "stripe_checkout_session_id": session.id,
    }).eq("ticket_order_id", order_id).execute()

    return {"checkout_url": session.url, "ticket_order_id": order_id}


def fulfill_ticket_order(order_id: str, payment_intent_id: str | None = None) -> bool:
    """Fulfill a ticket order: create tickets + RSVP. Returns True if fulfilled now."""
    supabase = get_supabase()

    order_row = (
        supabase.table("ticket_order")
        .select("*")
        .eq("ticket_order_id", order_id)
        .single()
        .execute()
    )
    order = order_row.data
    if order["status"] == "paid":
        return False  # already fulfilled (idempotent)

    # Mark as paid
    update_data: dict = {
        "status": "paid",
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }
    if payment_intent_id:
        update_data["stripe_payment_intent_id"] = payment_intent_id

    supabase.table("ticket_order").update(update_data).eq(
        "ticket_order_id", order_id
    ).execute()

    # Get person info for guest name and token
    person = (
        supabase.table("person")
        .select("person_id, first_name, last_name, supabase_user_id")
        .eq("person_id", order["person_id"])
        .single()
        .execute()
    )
    p = person.data
    guest_name = " ".join(x for x in [p.get("first_name", ""), p.get("last_name", "")] if x).strip() or "Gast"

    svc = get_supabase()

    # Create tickets using service supabase (bypasses RLS)
    from app.core.ticket_token import generate_ticket_token

    opt_row = None
    ticket_option_name = None
    if order["ticket_option_id"]:
        opt_row = svc.table("ticket_option").select("name").eq(
            "ticket_option_id", order["ticket_option_id"]
        ).single().execute()
        ticket_option_name = (opt_row.data or {}).get("name")

    existing_resp = (
        svc.table("ticket")
        .select("ticket_id", count="exact")
        .eq("event_id", order["event_id"])
        .eq("person_id", order["person_id"])
        .execute()
    )
    existing_count = existing_resp.count or 0

    payloads = []
    for i in range(order["quantity"]):
        ticket_nr = existing_count + i + 1
        qr_token = generate_ticket_token(
            order["event_id"], guest_name, ticket_nr, ticket_option_name
        )
        payload = {
            "event_id": order["event_id"],
            "person_id": order["person_id"],
            "qr_token": qr_token,
            "guest_name": guest_name,
            "ticket_order_id": order_id,
        }
        if order["ticket_option_id"]:
            payload["ticket_option_id"] = order["ticket_option_id"]
        payloads.append(payload)

    if payloads:
        svc.table("ticket").insert(payloads).execute()

    # Decrement ticket_option quantity_limit
    if order["ticket_option_id"]:
        limit_row = svc.table("ticket_option").select("quantity_limit").eq(
            "ticket_option_id", order["ticket_option_id"]
        ).single().execute()
        current_limit = (limit_row.data or {}).get("quantity_limit")
        if current_limit is not None:
            svc.table("ticket_option").update({
                "quantity_limit": max(0, current_limit - order["quantity"])
            }).eq("ticket_option_id", order["ticket_option_id"]).execute()

    # Set RSVP to Accepted
    existing_participation = (
        svc.table("event_participation")
        .select("event_participation_id")
        .eq("event_id", order["event_id"])
        .eq("person_id", order["person_id"])
        .maybe_single()
        .execute()
    )
    ep_data = getattr(existing_participation, "data", None) if existing_participation else None
    if ep_data:
        svc.table("event_participation").update({"status": "Accepted"}).eq(
            "event_participation_id", ep_data["event_participation_id"]
        ).execute()
    else:
        svc.table("event_participation").insert({
            "event_id": order["event_id"],
            "person_id": order["person_id"],
            "status": "Accepted",
        }).execute()

    logger.info("Fulfilled order %s: %d tickets created", order_id, len(payloads))
    return True


def expire_ticket_order(order_id: str) -> None:
    """Mark a ticket order as expired."""
    supabase = get_supabase()
    supabase.table("ticket_order").update({"status": "expired"}).eq(
        "ticket_order_id", order_id
    ).eq("status", "pending").execute()


def fail_ticket_order(order_id: str) -> None:
    """Mark a ticket order as failed."""
    supabase = get_supabase()
    supabase.table("ticket_order").update({"status": "failed"}).eq(
        "ticket_order_id", order_id
    ).eq("status", "pending").execute()


def cancel_ticket_order(event_id: str, person_id: str) -> dict:
    """Cancel a paid ticket order: refund via Stripe, delete tickets, update RSVP."""
    supabase = get_supabase()

    # Find the paid order for this person + event
    order_row = (
        supabase.table("ticket_order")
        .select("*")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .eq("status", "paid")
        .maybe_single()
        .execute()
    )
    order = getattr(order_row, "data", None) if order_row else None
    if not order:
        raise ValueError("no_paid_order")

    # Refund via Stripe if payment_intent is available
    refunded = False
    if order.get("stripe_payment_intent_id"):
        stripe_payment.create_refund(order["stripe_payment_intent_id"])
        refunded = True

    # Mark order as refunded
    supabase.table("ticket_order").update({
        "status": "refunded",
    }).eq("ticket_order_id", order["ticket_order_id"]).execute()

    # Delete tickets linked to this order
    supabase.table("ticket").delete().eq(
        "ticket_order_id", order["ticket_order_id"]
    ).execute()

    # Also delete any tickets for this person+event without an order link
    supabase.table("ticket").delete().eq(
        "event_id", event_id
    ).eq("person_id", person_id).execute()

    # Update RSVP to Declined
    participation = (
        supabase.table("event_participation")
        .select("event_participation_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .maybe_single()
        .execute()
    )
    ep_data = getattr(participation, "data", None) if participation else None
    if ep_data:
        supabase.table("event_participation").update({"status": "Declined"}).eq(
            "event_participation_id", ep_data["event_participation_id"]
        ).execute()

    # Restore ticket option quantity limit
    if order.get("ticket_option_id"):
        limit_row = (
            supabase.table("ticket_option")
            .select("quantity_limit")
            .eq("ticket_option_id", order["ticket_option_id"])
            .single()
            .execute()
        )
        current_limit = (limit_row.data or {}).get("quantity_limit")
        if current_limit is not None:
            supabase.table("ticket_option").update({
                "quantity_limit": current_limit + order["quantity"]
            }).eq("ticket_option_id", order["ticket_option_id"]).execute()

    logger.info("Cancelled order %s: refunded=%s", order["ticket_order_id"], refunded)
    return {"refunded": refunded, "amount_cents": order["amount_total_cents"]}


def get_payment_summary(event_id: str) -> dict:
    """Get aggregated payment stats for an event."""
    supabase = get_supabase()
    orders = (
        supabase.table("ticket_order")
        .select("amount_total_cents, application_fee_cents, status")
        .eq("event_id", event_id)
        .eq("status", "paid")
        .execute()
    )
    rows = orders.data or []
    gross = sum(r["amount_total_cents"] for r in rows)
    fees = sum(r["application_fee_cents"] for r in rows)
    return {
        "gross_cents": gross,
        "platform_fee_cents": fees,
        "net_cents": gross - fees,
        "paid_orders": len(rows),
    }
