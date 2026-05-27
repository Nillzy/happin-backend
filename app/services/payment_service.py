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


def _assert_host_stripe_ready(host_info: dict | None) -> None:
    if not host_info or not host_info.get("stripe_connect_account_id"):
        raise ValueError("host_not_onboarded")
    if not host_info.get("stripe_connect_charges_enabled"):
        raise ValueError("host_charges_not_enabled")


def require_stripe_for_paid_public_event(event_id: str, *, is_public: bool | None = None) -> None:
    """
    Public events with paid ticket options require an active Stripe Connect account.
    Free-only and private events are exempt.
    """
    supabase = get_supabase()

    event_row = (
        supabase.table("event")
        .select("is_public")
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )
    if not event_row or not event_row.data:
        raise ValueError("event_not_found")

    effective_is_public = (
        is_public if is_public is not None else event_row.data.get("is_public", True)
    )
    if not effective_is_public:
        return

    options = (
        supabase.table("ticket_option")
        .select("price")
        .eq("event_id", event_id)
        .execute()
    )
    has_paid = any(float(opt.get("price", 0) or 0) > 0 for opt in (options.data or []))
    if not has_paid:
        return

    _assert_host_stripe_ready(get_host_stripe_account(event_id))


def require_stripe_for_paid_public_tickets(
    event_id: str, options: list[dict], *, is_public: bool | None = None
) -> None:
    """Validate Stripe Connect before saving paid ticket options on a public event."""
    has_paid = any(float(opt.get("price", 0) or 0) > 0 for opt in options)
    if not has_paid:
        return

    supabase = get_supabase()
    event_row = (
        supabase.table("event")
        .select("is_public")
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )
    if not event_row or not event_row.data:
        raise ValueError("event_not_found")

    effective_is_public = (
        is_public if is_public is not None else event_row.data.get("is_public", True)
    )
    if not effective_is_public:
        return

    _assert_host_stripe_ready(get_host_stripe_account(event_id))


def _append_query_param(url: str, key: str, value: str) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{key}={value}"


def _expire_pending_order(order_id: str, event_id: str) -> None:
    expire_ticket_order(order_id)
    try:
        from app.services.waitlist_service import promote_next

        promote_next(event_id)
    except Exception:
        logger.exception("promote_next failed after checkout expired for event %s", event_id)


def sync_pending_checkout_with_stripe(supabase, order: dict) -> str | None:
    """
    Reconcile a pending order with Stripe session state.
    Returns Stripe session status, or None when there is no linked session.
    Expires local orders whose Stripe session is no longer open.
    """
    session_id = order.get("stripe_checkout_session_id")
    if not session_id:
        return None

    try:
        session = stripe_payment.retrieve_checkout_session(session_id)
    except Exception:
        logger.exception("Failed to retrieve checkout session %s", session_id)
        return None

    status = stripe_payment.checkout_session_status(session)
    payment_status = stripe_payment.checkout_session_payment_status(session)
    order_id = order["ticket_order_id"]
    event_id = order["event_id"]

    if status == "expired":
        _expire_pending_order(order_id, event_id)
        return status

    if status == "complete" and payment_status in ("unpaid", "failed"):
        fail_ticket_order(order_id)
        try:
            from app.services.waitlist_service import promote_next

            promote_next(event_id)
        except Exception:
            logger.exception("promote_next failed after payment failed for event %s", event_id)
        return status

    return status


def sync_pending_checkouts(supabase, event_id: str, person_id: str) -> None:
    """Sync all pending checkout orders for a user/event with Stripe."""
    rows = (
        supabase.table("ticket_order")
        .select("*")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .eq("status", "pending")
        .execute()
    )
    for order in rows.data or []:
        sync_pending_checkout_with_stripe(supabase, order)


def abandon_checkout(*, event_id: str, person_id: str) -> bool:
    """Invalidate open checkouts for an event (Stripe session + local orders)."""
    supabase = get_supabase()
    rows = (
        supabase.table("ticket_order")
        .select("*")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .eq("status", "pending")
        .execute()
    )
    orders = rows.data or []
    if not orders:
        return False

    abandoned = False
    for order in orders:
        session_id = order.get("stripe_checkout_session_id")
        if session_id:
            try:
                session = stripe_payment.retrieve_checkout_session(session_id)
                status = stripe_payment.checkout_session_status(session)
                payment_status = stripe_payment.checkout_session_payment_status(session)
                if status == "complete" and payment_status == "paid":
                    continue
                if status == "open":
                    stripe_payment.expire_checkout_session(session_id)
            except Exception:
                logger.exception("Failed to expire Stripe checkout session %s", session_id)

        _expire_pending_order(order["ticket_order_id"], event_id)
        abandoned = True

    return abandoned


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

    booking_service.expire_stale_pending_orders(supabase, event_id, person_id)
    sync_pending_checkouts(supabase, event_id, person_id)
    abandon_checkout(event_id=event_id, person_id=person_id)

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
    _assert_host_stripe_ready(host_info)

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
    cancel_url = _append_query_param(cancel_url, "event_id", event_id)

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

    if status == "refunded":
        return False

    if status == "expired" and payment_intent_id:
        update_data = {
            "status": "paid",
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "stripe_payment_intent_id": payment_intent_id,
        }
        claimed = (
            supabase.table("ticket_order")
            .update(update_data)
            .eq("ticket_order_id", order_id)
            .eq("status", "expired")
            .execute()
        )
        if claimed.data:
            status = "paid"
        else:
            order_row = (
                supabase.table("ticket_order")
                .select("*")
                .eq("ticket_order_id", order_id)
                .single()
                .execute()
            )
            order = order_row.data
            status = order["status"]

    if status == "failed":
        return False

    if status in ("expired",):
        return False

    if status == "paid" and _order_has_tickets(supabase, order_id):
        return True

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
                return True
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


def _refund_single_order(order: dict, idempotency_key: str | None = None) -> dict:
    """Refund a single paid ticket_order via Stripe and update DB state.

    Returns a result dict: {"refunded": bool, "amount_cents": int, "order_id": str, "error": str | None}.
    On success: order.status = 'refunded', tickets deleted, participation set to 'Declined' if no tickets remain.
    On failure: order is left untouched and the error reason is returned in 'error'.
    """
    supabase = get_supabase()
    order_id = order["ticket_order_id"]

    payment_intent_id = _resolve_payment_intent_id(order)
    if not payment_intent_id:
        return {"refunded": False, "amount_cents": 0, "order_id": order_id, "error": "refund_not_possible"}

    event_id = order["event_id"]
    person_id = order["person_id"]

    try:
        refund = stripe_payment.create_refund(
            payment_intent_id,
            idempotency_key=idempotency_key or f"refund-{order_id}",
        )
    except Exception:  # pragma: no cover — Stripe SDK exceptions
        logger.exception("Stripe refund failed for order %s", order_id)
        return {"refunded": False, "amount_cents": 0, "order_id": order_id, "error": "refund_failed"}

    refund_status = getattr(refund, "status", None) or refund.get("status")
    if refund_status not in ("succeeded", "pending"):
        return {"refunded": False, "amount_cents": 0, "order_id": order_id, "error": "refund_failed"}

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

    return {"refunded": True, "amount_cents": order["amount_total_cents"], "order_id": order_id, "error": None}


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

    result = _refund_single_order(order)
    if not result["refunded"]:
        # Surface the original error code (refund_not_possible / refund_failed)
        raise ValueError(result["error"])

    order_id = order["ticket_order_id"]

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
        "amount_cents": result["amount_cents"],
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
