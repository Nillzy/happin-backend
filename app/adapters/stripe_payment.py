"""Thin wrapper around the Stripe SDK for Connect operations."""

from __future__ import annotations

import time
import logging
from typing import Any

from stripe import StripeClient, Webhook, SignatureVerificationError

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: StripeClient | None = None


def get_stripe_client() -> StripeClient:
    global _client
    if _client is None:
        if not settings.STRIPE_SECRET_KEY:
            raise RuntimeError("STRIPE_SECRET_KEY is not configured")
        _client = StripeClient(settings.STRIPE_SECRET_KEY)
    return _client


def create_express_account(email: str | None = None, country: str = "DE") -> Any:
    """Create an Express connected account."""
    client = get_stripe_client()
    params: dict[str, Any] = {
        "type": "express",
        "country": country,
        "capabilities": {
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
        },
    }
    if email:
        params["email"] = email
    return client.v1.accounts.create(params=params)


def create_account_link(account_id: str, refresh_url: str, return_url: str) -> Any:
    """Create an Account Link for Express onboarding."""
    client = get_stripe_client()
    return client.v1.account_links.create(params={
        "account": account_id,
        "refresh_url": refresh_url,
        "return_url": return_url,
        "type": "account_onboarding",
    })


def create_login_link(account_id: str) -> Any:
    """Create a Login Link for the Express Dashboard."""
    client = get_stripe_client()
    return client.v1.accounts.create_login_link(account_id)


def set_manual_payouts(account_id: str) -> None:
    """Set payout schedule to manual for a connected account."""
    client = get_stripe_client()
    client.v1.accounts.update(
        account_id,
        params={
            "settings": {
                "payouts": {
                    "schedule": {"interval": "manual"},
                },
            },
        },
    )


def retrieve_account(account_id: str) -> Any:
    """Retrieve a connected account to check capabilities."""
    client = get_stripe_client()
    return client.v1.accounts.retrieve(account_id)


def create_checkout_session(
    *,
    line_items: list[dict[str, Any]],
    destination_account_id: str,
    application_fee_amount: int,
    success_url: str,
    cancel_url: str,
    metadata: dict[str, str],
    customer_email: str | None = None,
    expires_at: int | None = None,
    idempotency_key: str | None = None,
) -> Any:
    """Create a Stripe Checkout Session with destination charge."""
    client = get_stripe_client()
    params: dict[str, Any] = {
        "mode": "payment",
        "line_items": line_items,
        "payment_intent_data": {
            "application_fee_amount": application_fee_amount,
            "transfer_data": {"destination": destination_account_id},
            "metadata": metadata,
        },
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": metadata,
    }
    if customer_email:
        params["customer_email"] = customer_email
    if expires_at:
        params["expires_at"] = expires_at
    else:
        params["expires_at"] = int(time.time()) + 30 * 60  # 30 min default

    options: dict[str, Any] = {}
    if idempotency_key:
        options["idempotency_key"] = idempotency_key

    return client.v1.checkout.sessions.create(params=params, options=options)


def retrieve_checkout_session(session_id: str) -> Any:
    """Retrieve a Checkout Session by ID."""
    client = get_stripe_client()
    return client.v1.checkout.sessions.retrieve(session_id)


def expire_checkout_session(session_id: str) -> Any:
    """Expire an open Checkout Session so it can no longer be completed."""
    client = get_stripe_client()
    return client.v1.checkout.sessions.expire(session_id)


def checkout_session_status(session: Any) -> str:
    if isinstance(session, dict):
        return str(session.get("status") or "")
    return str(getattr(session, "status", "") or "")


def checkout_session_url(session: Any) -> str | None:
    if isinstance(session, dict):
        url = session.get("url")
        return str(url) if url else None
    url = getattr(session, "url", None)
    return str(url) if url else None


def checkout_session_payment_status(session: Any) -> str:
    if isinstance(session, dict):
        return str(session.get("payment_status") or "")
    return str(getattr(session, "payment_status", "") or "")


def retrieve_balance(account_id: str) -> Any:
    """Retrieve the balance of a connected account."""
    client = get_stripe_client()
    return client.v1.balance.retrieve(options={"stripe_account": account_id})


def create_refund(
    payment_intent_id: str,
    amount: int | None = None,
    *,
    idempotency_key: str | None = None,
) -> Any:
    """Refund a destination charge; reverse transfer and application fee to host."""
    client = get_stripe_client()
    params: dict[str, Any] = {
        "payment_intent": payment_intent_id,
        "reverse_transfer": True,
        "refund_application_fee": True,
    }
    if amount is not None:
        params["amount"] = amount
    options: dict[str, Any] = {}
    if idempotency_key:
        options["idempotency_key"] = idempotency_key
    return client.v1.refunds.create(params=params, options=options or None)


def create_payout(account_id: str, amount: int, currency: str = "eur") -> Any:
    """Create a payout to the connected account's bank."""
    client = get_stripe_client()
    return client.v1.payouts.create(
        params={"amount": amount, "currency": currency},
        options={"stripe_account": account_id},
    )


def construct_webhook_event(payload: bytes, sig_header: str) -> Any:
    """Verify and construct a Stripe webhook event."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
    try:
        return Webhook.construct_event(
            payload.decode("utf-8"),
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except SignatureVerificationError:
        raise
    except ValueError:
        raise
