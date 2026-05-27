"""Persistent Stripe webhook inbox — store first, process with retries."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.core.supabase import get_supabase_admin
from app.services import payment_service
from app.services.waitlist_service import promote_next

logger = logging.getLogger(__name__)

MAX_WEBHOOK_ATTEMPTS = 5
_RETRY_BACKOFF_SECONDS = 0.5


class WebhookProcessingError(Exception):
    """Raised when a webhook event cannot be processed successfully."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payment_intent_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("id")
    return getattr(value, "id", None) or str(value)


def _object_get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def persist_webhook_event(*, stripe_event_id: str, event_type: str, payload: dict) -> dict:
    """Insert webhook payload or return the existing row (idempotent on stripe_event_id)."""
    supabase = get_supabase_admin()
    try:
        existing = (
            supabase.table("stripe_webhook_event")
            .select("*")
            .eq("stripe_event_id", stripe_event_id)
            .maybe_single()
            .execute()
        )
        if existing is not None and existing.data:
            return existing.data

        inserted = (
            supabase.table("stripe_webhook_event")
            .insert(
                {
                    "stripe_event_id": stripe_event_id,
                    "event_type": event_type,
                    "payload": payload,
                    "status": "pending",
                    "max_attempts": MAX_WEBHOOK_ATTEMPTS,
                }
            )
            .execute()
        )
        if not inserted.data:
            raise WebhookProcessingError("Failed to persist stripe webhook event")
        return inserted.data[0]
    except Exception as exc:
        code = getattr(exc, "code", None)
        if code == "PGRST205":
            raise WebhookProcessingError(
                "stripe_webhook_event table missing — apply migration "
                "20260527120000_stripe_webhook_events.sql in Supabase"
            ) from exc
        raise


def _update_webhook_record(webhook_event_id: str, patch: dict) -> None:
    supabase = get_supabase_admin()
    patch["updated_at"] = _now_iso()
    supabase.table("stripe_webhook_event").update(patch).eq(
        "webhook_event_id", webhook_event_id
    ).execute()


def dispatch_stripe_event(event_type: str, data: Any) -> None:
    """Run business logic for a verified Stripe event."""
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
        logger.debug("Unhandled Stripe event type: %s", event_type)


def process_persisted_webhook(record: dict) -> None:
    """
    Process a persisted webhook with inline retries.
    Raises WebhookProcessingError when all attempts are exhausted.
    """
    if record["status"] == "success":
        return

    if record["status"] == "failed":
        _update_webhook_record(
            record["webhook_event_id"],
            {"status": "pending", "attempt_count": 0, "last_error": None},
        )
        record = {
            **record,
            "status": "pending",
            "attempt_count": 0,
            "last_error": None,
        }

    webhook_event_id = record["webhook_event_id"]
    event_type = record["event_type"]
    payload = record["payload"]
    event_data = payload.get("data", {}).get("object", payload)
    max_attempts = record.get("max_attempts") or MAX_WEBHOOK_ATTEMPTS
    attempt_count = record.get("attempt_count") or 0

    last_error: str | None = None

    while attempt_count < max_attempts:
        attempt_count += 1
        _update_webhook_record(
            webhook_event_id,
            {"status": "processing", "attempt_count": attempt_count, "last_error": None},
        )
        try:
            dispatch_stripe_event(event_type, event_data)
            _update_webhook_record(
                webhook_event_id,
                {
                    "status": "success",
                    "processed_at": _now_iso(),
                    "last_error": None,
                },
            )
            logger.info(
                "Webhook %s processed successfully on attempt %s",
                record["stripe_event_id"],
                attempt_count,
            )
            return
        except Exception as exc:
            last_error = str(exc)
            logger.exception(
                "Webhook %s attempt %s/%s failed",
                record["stripe_event_id"],
                attempt_count,
                max_attempts,
            )
            if attempt_count >= max_attempts:
                _update_webhook_record(
                    webhook_event_id,
                    {"status": "failed", "last_error": last_error},
                )
                raise WebhookProcessingError(last_error) from exc

            _update_webhook_record(
                webhook_event_id,
                {"status": "pending", "last_error": last_error},
            )
            time.sleep(_RETRY_BACKOFF_SECONDS * attempt_count)

    raise WebhookProcessingError(last_error or "Webhook processing failed")


def ingest_and_process_webhook(*, stripe_event: Any, raw_payload: bytes) -> dict:
    """
    Persist webhook payload, then process with retries.
    Returns a small status dict for the HTTP handler.
    """
    payload_dict = json.loads(raw_payload.decode("utf-8"))
    stripe_event_id = stripe_event.id
    event_type = stripe_event.type

    record = persist_webhook_event(
        stripe_event_id=stripe_event_id,
        event_type=event_type,
        payload=payload_dict,
    )

    if record["status"] == "success":
        return {"received": True, "status": "success", "duplicate": True}

    process_persisted_webhook(record)
    return {"received": True, "status": "success"}


def _require_fulfillment(order_id: str, payment_intent_id: str | None) -> None:
    fulfilled = payment_service.fulfill_ticket_order(
        order_id, payment_intent_id=payment_intent_id
    )
    if not fulfilled:
        raise WebhookProcessingError(f"Ticket order {order_id} could not be fulfilled")


def _handle_checkout_completed(session) -> None:
    metadata = _object_get(session, "metadata") or {}
    order_id = metadata.get("ticket_order_id")
    if not order_id:
        return
    if _object_get(session, "payment_status") == "paid":
        _require_fulfillment(order_id, _payment_intent_id(_object_get(session, "payment_intent")))


def _handle_async_payment_succeeded(session) -> None:
    metadata = _object_get(session, "metadata") or {}
    order_id = metadata.get("ticket_order_id")
    if not order_id:
        return
    _require_fulfillment(order_id, _payment_intent_id(_object_get(session, "payment_intent")))


def _handle_async_payment_failed(session) -> None:
    metadata = _object_get(session, "metadata") or {}
    order_id = metadata.get("ticket_order_id")
    event_id = metadata.get("event_id")
    if order_id:
        payment_service.fail_ticket_order(order_id)
        if event_id:
            try:
                promote_next(event_id)
            except Exception:
                logger.exception("promote_next failed after payment failed for event %s", event_id)


def _handle_checkout_expired(session) -> None:
    metadata = _object_get(session, "metadata") or {}
    order_id = metadata.get("ticket_order_id")
    event_id = metadata.get("event_id")
    if order_id:
        payment_service.expire_ticket_order(order_id)
        if event_id:
            try:
                promote_next(event_id)
            except Exception:
                logger.exception("promote_next failed after checkout expired for event %s", event_id)


def _handle_payment_intent_succeeded(payment_intent) -> None:
    metadata = _object_get(payment_intent, "metadata") or {}
    order_id = metadata.get("ticket_order_id")
    if not order_id:
        return
    supabase = get_supabase_admin()
    supabase.table("ticket_order").update(
        {"stripe_payment_intent_id": _object_get(payment_intent, "id")}
    ).eq("ticket_order_id", order_id).is_("stripe_payment_intent_id", "null").execute()


def _handle_account_updated(account) -> None:
    supabase = get_supabase_admin()
    account_id = _object_get(account, "id")
    charges_enabled = bool(_object_get(account, "charges_enabled", False))
    payouts_enabled = bool(_object_get(account, "payouts_enabled", False))

    update_data: dict = {
        "stripe_connect_charges_enabled": charges_enabled,
        "stripe_connect_payouts_enabled": payouts_enabled,
    }
    if charges_enabled and payouts_enabled:
        update_data["stripe_connect_onboarding_completed_at"] = _now_iso()

    supabase.table("person").update(update_data).eq(
        "stripe_connect_account_id", account_id
    ).execute()
