"""Payment endpoints — Stripe Connect onboarding, checkout, webhooks, payouts."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.supabase import get_supabase_admin
from app.services import payment_service, person_service
from app.adapters import stripe_payment
from app.schemas.payments import (
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    CheckoutOrderStatusResponse,
    ConnectOnboardingResponse,
    ConnectStatusResponse,
    DashboardLinkResponse,
    PaymentSummaryResponse,
    PayoutResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Connect Onboarding ────────────────────────────────────────────────────────


@router.post("/connect/onboarding-link", response_model=ConnectOnboardingResponse)
async def create_onboarding_link(
    event_id: str | None = None,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Create or retrieve Express account + Account Link for onboarding."""
    try:
        token = credentials.credentials
        person = person_service.get_or_create_person(
            supabase_user_id=user.user.id,
            email=user.user.email,
            token=token,
        )
        person_id = person["person_id"]
        supabase = get_supabase_admin()

        # Check if already has account
        person_row = (
            supabase.table("person")
            .select("stripe_connect_account_id, stripe_connect_charges_enabled")
            .eq("person_id", person_id)
            .single()
            .execute()
        )
        account_id = person_row.data.get("stripe_connect_account_id")

        if not account_id:
            # Create Express account
            account = stripe_payment.create_express_account(email=user.user.email)
            account_id = account.id
            supabase.table("person").update({
                "stripe_connect_account_id": account_id,
            }).eq("person_id", person_id).execute()

            # Set manual payouts
            stripe_payment.set_manual_payouts(account_id)

        # Create Account Link (requires https:// URLs, not deep-links)
        refresh_url = settings.STRIPE_CONNECT_REFRESH_URL or "https://happin.fun/connect/refresh"
        return_url = settings.STRIPE_CONNECT_RETURN_URL or "https://happin.fun/connect/return"
        if event_id:
            separator = "&" if "?" in return_url else "?"
            return_url += f"{separator}event_id={event_id}"
            sep2 = "&" if "?" in refresh_url else "?"
            refresh_url += f"{sep2}event_id={event_id}"

        link = stripe_payment.create_account_link(
            account_id=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
        )
        return ConnectOnboardingResponse(url=link.url, account_id=account_id)
    except Exception as e:
        logger.exception("Onboarding link creation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connect/status", response_model=ConnectStatusResponse)
async def get_connect_status(
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Get current Connect onboarding status."""
    token = credentials.credentials
    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=token,
    )
    supabase = get_supabase_admin()
    person_row = (
        supabase.table("person")
        .select(
            "stripe_connect_account_id, stripe_connect_charges_enabled, "
            "stripe_connect_payouts_enabled, stripe_connect_onboarding_completed_at"
        )
        .eq("person_id", person["person_id"])
        .single()
        .execute()
    )
    data = person_row.data
    return ConnectStatusResponse(
        has_account=bool(data.get("stripe_connect_account_id")),
        charges_enabled=data.get("stripe_connect_charges_enabled", False),
        payouts_enabled=data.get("stripe_connect_payouts_enabled", False),
        onboarding_complete=data.get("stripe_connect_onboarding_completed_at") is not None,
    )


@router.post("/connect/dashboard-link", response_model=DashboardLinkResponse)
async def create_dashboard_link(
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Create an Express Dashboard login link for the host."""
    token = credentials.credentials
    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=token,
    )
    supabase = get_supabase_admin()
    person_row = (
        supabase.table("person")
        .select("stripe_connect_account_id, stripe_connect_charges_enabled")
        .eq("person_id", person["person_id"])
        .single()
        .execute()
    )
    account_id = person_row.data.get("stripe_connect_account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="No Stripe account connected")

    link = stripe_payment.create_login_link(account_id)
    return DashboardLinkResponse(url=link.url)


# ── Checkout ──────────────────────────────────────────────────────────────────


@router.post(
    "/events/{event_id}/checkout-session",
    response_model=CreateCheckoutSessionResponse,
)
async def create_checkout_session(
    event_id: str,
    body: CreateCheckoutSessionRequest,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Create a Stripe Checkout Session for ticket purchase."""
    token = credentials.credentials
    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=token,
    )
    try:
        result = payment_service.create_checkout_session(
            event_id=event_id,
            person_id=person["person_id"],
            ticket_option_id=body.ticket_option_id,
            quantity=body.quantity,
            person_email=user.user.email,
        )
        return CreateCheckoutSessionResponse(**result)
    except ValueError as e:
        error_map = {
            "ticket_option_free": (400, "This ticket option is free — use direct booking"),
            "ticket_option_wrong_event": (400, "Ticket option does not belong to this event"),
            "ticket_option_required": (400, "A ticket option is required for checkout"),
            "event_full": (409, "Event is fully booked"),
            "event_not_found": (404, "Event not found"),
            "ticket_option_sold_out": (409, "Ticket option sold out"),
            "max_tickets_exceeded": (409, "Maximum tickets per person exceeded"),
            "checkout_pending": (409, "You already have a pending checkout for this event"),
            "host_not_onboarded": (402, "Host has not completed payment setup"),
            "host_charges_not_enabled": (402, "Host payment account is not yet active"),
        }
        code, detail = error_map.get(str(e), (400, str(e)))
        raise HTTPException(status_code=code, detail=detail)


@router.get(
    "/checkout/orders/status",
    response_model=CheckoutOrderStatusResponse,
)
async def get_checkout_order_status(
    session_id: str,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Poll checkout fulfillment by Stripe session ID (success page)."""
    token = credentials.credentials
    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=token,
    )
    try:
        return payment_service.get_checkout_order_status(
            session_id=session_id,
            person_id=person["person_id"],
        )
    except ValueError as e:
        if str(e) == "order_not_found":
            raise HTTPException(status_code=404, detail="Order not found for this session")
        raise HTTPException(status_code=400, detail=str(e))


# ── Cancel / Refund ───────────────────────────────────────────────────────────


@router.post("/events/{event_id}/tickets/cancel")
async def cancel_tickets(
    event_id: str,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Cancel a user's tickets for an event and trigger a Stripe refund."""
    token = credentials.credentials
    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=token,
    )
    try:
        result = payment_service.cancel_ticket_order(
            event_id=event_id,
            person_id=person["person_id"],
        )
        return result
    except ValueError as e:
        error_map = {
            "no_paid_order": (404, "No active paid ticket order found for this event"),
            "refund_not_possible": (502, "Payment cannot be refunded. Contact support."),
            "refund_failed": (502, "Refund could not be processed. Please try again later."),
        }
        code, detail = error_map.get(str(e), (400, str(e)))
        raise HTTPException(status_code=code, detail=detail)


# ── Webhooks ──────────────────────────────────────────────────────────────────


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (no JWT auth, uses signature verification)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe_payment.construct_webhook_event(payload, sig_header)
    except Exception:
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.type
    data = event.data.object
    logger.info("Webhook received: %s", event_type)

    try:
        if event_type == "checkout.session.completed":
            _handle_checkout_completed(data)
        elif event_type == "checkout.session.async_payment_succeeded":
            _handle_async_payment_succeeded(data)
        elif event_type == "checkout.session.async_payment_failed":
            _handle_async_payment_failed(data)
        elif event_type == "checkout.session.expired":
            _handle_checkout_expired(data)
        elif event_type == "payment_intent.succeeded":
            _handle_payment_intent_succeeded(data)
        elif event_type == "account.updated":
            _handle_account_updated(data)
        elif event_type in ("payout.paid", "payout.failed"):
            logger.info("Payout event: %s", event_type)
        else:
            logger.debug("Unhandled event type: %s", event_type)
    except Exception:
        logger.exception("Webhook handler failed for event: %s", event_type)
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    return {"received": True}


def _handle_checkout_completed(session) -> None:
    """Fulfill only if payment_status is 'paid' (synchronous payment methods)."""
    order_id = (session.metadata or {}).get("ticket_order_id")
    if not order_id:
        return
    if session.payment_status == "paid":
        payment_service.fulfill_ticket_order(
            order_id, payment_intent_id=session.payment_intent
        )
    # If payment_status is 'unpaid', wait for async_payment_succeeded


def _handle_async_payment_succeeded(session) -> None:
    """Fulfill for delayed payment methods (SEPA, etc.)."""
    order_id = (session.metadata or {}).get("ticket_order_id")
    if not order_id:
        return
    payment_service.fulfill_ticket_order(
        order_id, payment_intent_id=session.payment_intent
    )


def _handle_async_payment_failed(session) -> None:
    metadata = session.metadata or {}
    order_id = metadata.get("ticket_order_id")
    event_id = metadata.get("event_id")
    if order_id:
        payment_service.fail_ticket_order(order_id)
        if event_id:
            try:
                from app.services.waitlist_service import promote_next
                promote_next(event_id)
            except Exception:
                logger.exception("promote_next failed after payment failed for event %s", event_id)


def _handle_checkout_expired(session) -> None:
    metadata = session.metadata or {}
    order_id = metadata.get("ticket_order_id")
    event_id = metadata.get("event_id")
    if order_id:
        payment_service.expire_ticket_order(order_id)
        if event_id:
            try:
                from app.services.waitlist_service import promote_next
                promote_next(event_id)
            except Exception:
                logger.exception("promote_next failed after checkout expired for event %s", event_id)


def _handle_payment_intent_succeeded(payment_intent) -> None:
    """Store payment intent on order; fulfillment is via checkout session webhooks."""
    order_id = (payment_intent.metadata or {}).get("ticket_order_id")
    if not order_id:
        return
    supabase = get_supabase_admin()
    supabase.table("ticket_order").update({
        "stripe_payment_intent_id": payment_intent.id,
    }).eq("ticket_order_id", order_id).is_("stripe_payment_intent_id", "null").execute()


def _handle_account_updated(account) -> None:
    """Sync charges_enabled/payouts_enabled to person table."""
    supabase = get_supabase_admin()
    account_id = account.id
    charges_enabled = getattr(account, "charges_enabled", False)
    payouts_enabled = getattr(account, "payouts_enabled", False)

    update_data: dict = {
        "stripe_connect_charges_enabled": charges_enabled,
        "stripe_connect_payouts_enabled": payouts_enabled,
    }
    if charges_enabled and payouts_enabled:
        update_data["stripe_connect_onboarding_completed_at"] = (
            datetime.now(timezone.utc).isoformat()
        )

    supabase.table("person").update(update_data).eq(
        "stripe_connect_account_id", account_id
    ).execute()


# ── Payment Summary & Payouts ─────────────────────────────────────────────────


@router.get("/events/{event_id}/payments/summary", response_model=PaymentSummaryResponse)
async def get_payment_summary(
    event_id: str,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Get payment summary for an event (host only)."""
    token = credentials.credentials
    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=token,
    )
    # Verify host
    supabase = get_supabase_admin()
    host_check = (
        supabase.table("event_host")
        .select("event_host_id")
        .eq("event_id", event_id)
        .eq("person_id", person["person_id"])
        .maybe_single()
        .execute()
    )
    if not host_check.data:
        raise HTTPException(status_code=403, detail="Not a host of this event")

    summary = payment_service.get_payment_summary(event_id)
    return PaymentSummaryResponse(**summary)


@router.post("/events/{event_id}/payout", response_model=PayoutResponse)
async def request_payout(
    event_id: str,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Request payout for event revenue (host only, after event ends)."""
    token = credentials.credentials
    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=token,
    )
    supabase = get_supabase_admin()

    # Verify host
    host_check = (
        supabase.table("event_host")
        .select("event_host_id")
        .eq("event_id", event_id)
        .eq("person_id", person["person_id"])
        .maybe_single()
        .execute()
    )
    if not host_check.data:
        raise HTTPException(status_code=403, detail="Not a host of this event")

    # Check event is in the past
    event_row = (
        supabase.table("event")
        .select("starts_at")
        .eq("event_id", event_id)
        .single()
        .execute()
    )
    starts_at_raw = event_row.data["starts_at"]
    starts_at = datetime.fromisoformat(str(starts_at_raw).replace("Z", "+00:00"))
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    if starts_at > datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Event has not ended yet")

    payout_host = payment_service.get_host_stripe_account(event_id)
    if not payout_host:
        raise HTTPException(status_code=400, detail="No payout recipient configured for this event")
    account_id = payout_host.get("stripe_connect_account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="No Stripe account connected")

    person_row = (
        supabase.table("person")
        .select("stripe_connect_payouts_enabled")
        .eq("person_id", payout_host["person_id"])
        .single()
        .execute()
    )
    if not person_row.data.get("stripe_connect_payouts_enabled"):
        raise HTTPException(status_code=400, detail="Payouts not enabled on account")

    # Check available balance
    balance = stripe_payment.retrieve_balance(account_id)
    available = 0
    for b in balance.available:
        if b.currency == "eur":
            available = b.amount
            break

    if available <= 0:
        raise HTTPException(status_code=400, detail="No available balance to pay out")

    payout = stripe_payment.create_payout(account_id, available, "eur")
    return PayoutResponse(
        payout_id=payout.id,
        amount_cents=available,
        currency="eur",
    )
