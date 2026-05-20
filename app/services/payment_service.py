"""Payment business logic — checkout, fulfillment, payouts."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.adapters import stripe_payment
from app.core.config import settings
from app.core.supabase import get_supabase_admin as get_supabase
from app.services import booking_service, ticket_service

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

    opt_data = booking_service.validate_booking(
        supabase,
        event_id=event_id,
        person_id=person_id,
        quantity=quantity,
        ticket_option_id=ticket_option_id,
        is_checkout=True,
    )
    unit_price_cents = int(float(opt_data["price"]) * 100)

    event_row = (
        supabase.table("event")
        .select("title")
        .eq("event_id", event_id)
        .single()
        .execute()
    )

    host_info = get_host_stripe_account(event_id)
    if not host_info or not host_info.get("stripe_connect_account_id"):
        raise ValueError("host_not_onboarded")
    if not host_info.get("stripe_connect_charges_enabled"):
        raise ValueError("host_charges_not_enabled")

    destination_account = host_info["stripe_connect_account_id"]
    amount_total_cents = unit_price_cents * quantity
    fee_cents = calculate_application_fee(amount_total_cents)

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

    order_metadata = {
        "ticket_order_id": order_id,
        "event_id": event_id,
        "person_id": person_id,
    }

    try:
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
            metadata=order_metadata,
            customer_email=person_email,
            idempotency_key=order_id,
        )
        supabase.table("ticket_order").update({
            "stripe_checkout_session_id": session.id,
        }).eq("ticket_order_id", order_id).execute()
    except Exception:
        expire_ticket_order(order_id)
        raise

    return {"checkout_url": session.url, "ticket_order_id": order_id}


def _order_has_tickets(svc, order_id: str) -> bool:
    rows = (
        svc.table("ticket")
        .select("ticket_id")
        .eq("ticket_order_id", order_id)
        .limit(1)
        .execute()
    )
    return bool(rows.data)


def _resolve_payment_intent_id(order: dict) -> str | None:
    """Payment intent from order row or Stripe Checkout session."""
    pi = order.get("stripe_payment_intent_id")
    if pi:
        return pi
    session_id = order.get("stripe_checkout_session_id")
    if not session_id:
        return None
    session = stripe_payment.retrieve_checkout_session(session_id)
    pi = getattr(session, "payment_intent", None)
    if pi is None and isinstance(session, dict):
        pi = session.get("payment_intent")
    if isinstance(pi, str):
        return pi
    if pi is not None:
        return getattr(pi, "id", None) or str(pi)
    return None


def fulfill_ticket_order(order_id: str, payment_intent_id: str | None = None) -> bool:
    """Fulfill a ticket order: claim paid status, then create tickets. Idempotent."""
    supabase = get_supabase()

    order_row = (
        supabase.table("ticket_order")
        .select("*")
        .eq("ticket_order_id", order_id)
        .single()
        .execute()
    )
    order = order_row.data
    status = order["status"]

    if status in ("refunded", "expired", "failed"):
        return False

    if status == "paid" and _order_has_tickets(supabase, order_id):
        return False

    if status not in ("pending", "paid"):
        return False

    should_create_tickets = False

    if status == "pending":
        update_data: dict = {
            "status": "paid",
            "paid_at": datetime.now(timezone.utc).isoformat(),
        }
        if payment_intent_id:
            update_data["stripe_payment_intent_id"] = payment_intent_id
        claimed = (
            supabase.table("ticket_order")
            .update(update_data)
            .eq("ticket_order_id", order_id)
            .eq("status", "pending")
            .execute()
        )
        should_create_tickets = bool(claimed.data)
        if not should_create_tickets:
            order_row = (
                supabase.table("ticket_order")
                .select("*")
                .eq("ticket_order_id", order_id)
                .single()
                .execute()
            )
            order = order_row.data
            if order["status"] == "paid" and _order_has_tickets(supabase, order_id):
                return False
            should_create_tickets = order["status"] == "paid" and not _order_has_tickets(
                supabase, order_id
            )
    else:
        if payment_intent_id and not order.get("stripe_payment_intent_id"):
            supabase.table("ticket_order").update({
                "stripe_payment_intent_id": payment_intent_id,
            }).eq("ticket_order_id", order_id).execute()
        should_create_tickets = not _order_has_tickets(supabase, order_id)

    if should_create_tickets:
        ticket_service.create_tickets_for_order(
            supabase,
            ticket_order_id=order_id,
            event_id=order["event_id"],
            person_id=order["person_id"],
            ticket_option_id=order.get("ticket_option_id"),
            quantity=order["quantity"],
        )

    logger.info("Fulfilled order %s", order_id)
    return True


def get_checkout_order_status(session_id: str, person_id: str) -> dict:
    """Return fulfillment state for a checkout session owned by the user."""
    supabase = get_supabase()
    order_row = (
        supabase.table("ticket_order")
        .select("ticket_order_id, event_id, person_id, status")
        .eq("stripe_checkout_session_id", session_id)
        .maybe_single()
        .execute()
    )
    order = getattr(order_row, "data", None) if order_row else None
    if not order or order["person_id"] != person_id:
        raise ValueError("order_not_found")

    fulfilled = order["status"] == "paid" and _order_has_tickets(supabase, order["ticket_order_id"])
    return {
        "order_status": order["status"],
        "fulfilled": fulfilled,
        "event_id": order["event_id"],
        "ticket_order_id": order["ticket_order_id"],
    }


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
    """Cancel the latest paid ticket order: Stripe refund first, then DB updates."""
    supabase = get_supabase()

    paid_rows = (
        supabase.table("ticket_order")
        .select("*")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .eq("status", "paid")
        .order("paid_at", desc=True)
        .limit(1)
        .execute()
    )
    order = (paid_rows.data or [None])[0]
    if not order:
        refunded_rows = (
            supabase.table("ticket_order")
            .select("amount_total_cents")
            .eq("event_id", event_id)
            .eq("person_id", person_id)
            .eq("status", "refunded")
            .order("paid_at", desc=True)
            .limit(1)
            .execute()
        )
        prev = (refunded_rows.data or [None])[0]
        if prev:
            return {"refunded": True, "amount_cents": prev["amount_total_cents"]}
        raise ValueError("no_paid_order")

    order_id = order["ticket_order_id"]
    payment_intent_id = _resolve_payment_intent_id(order)
    if not payment_intent_id:
        raise ValueError("refund_not_possible")

    refund = stripe_payment.create_refund(
        payment_intent_id,
        idempotency_key=f"refund-{order_id}",
    )
    refund_status = getattr(refund, "status", None) or refund.get("status")
    if refund_status not in ("succeeded", "pending"):
        raise ValueError("refund_failed")

    supabase.table("ticket_order").update({
        "status": "refunded",
        "stripe_payment_intent_id": payment_intent_id,
    }).eq("ticket_order_id", order_id).eq("status", "paid").execute()

    supabase.table("ticket").delete().eq("ticket_order_id", order_id).execute()

    remaining_tickets = (
        supabase.table("ticket")
        .select("ticket_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .limit(1)
        .execute()
    )
    if not remaining_tickets.data:
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

    logger.info("Cancelled order %s", order_id)
    return {
        "refunded": True,
        "amount_cents": order["amount_total_cents"],
    }


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
