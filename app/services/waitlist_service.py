"""Waitlist business logic — join, leave, position, promotion."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from app.core.supabase import get_supabase_admin, get_supabase_for_user
from app.services import booking_service

logger = logging.getLogger(__name__)


def _count_notified(supabase, event_id: str) -> int:
    result = (
        supabase.table("event_waitlist")
        .select("waitlist_id", count="exact")
        .eq("event_id", event_id)
        .eq("status", "notified")
        .execute()
    )
    return result.count or 0


def _get_position_count(supabase, event_id: str, joined_at: str) -> int:
    """Count 'waiting' entries that joined before the given timestamp."""
    ahead = (
        supabase.table("event_waitlist")
        .select("waitlist_id", count="exact")
        .eq("event_id", event_id)
        .eq("status", "waiting")
        .lt("joined_at", joined_at)
        .execute()
    )
    return ahead.count or 0


def join_waitlist(event_id: str, person_id: str, token: str) -> dict:
    """Add person to the event waitlist. Returns {waitlist_id, position}."""
    admin_sb = get_supabase_admin()
    user_sb = get_supabase_for_user(token)

    # Validate event
    event_rows = (
        admin_sb.table("event")
        .select("event_id, max_capacity, is_free, waitlist_promotion_hours, cancelled_at")
        .eq("event_id", event_id)
        .limit(1)
        .execute()
    )
    if not event_rows.data or event_rows.data[0].get("cancelled_at"):
        raise ValueError("event_not_found")
    event_data = event_rows.data[0]
    if not event_data.get("max_capacity"):
        raise ValueError("event_no_capacity_limit")

    # Check not host
    host_rows = (
        admin_sb.table("event_host")
        .select("event_host_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .limit(1)
        .execute()
    )
    if host_rows.data:
        raise ValueError("host_cannot_join_waitlist")

    # Check not already a participant (has an active ticket)
    ticket_check = (
        admin_sb.table("ticket")
        .select("ticket_id", count="exact")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .execute()
    )
    if (ticket_check.count or 0) > 0:
        raise ValueError("already_participant")

    # Expire stale promotions, then check event is actually full
    expire_stale_promotions(event_id)
    ticket_count = booking_service.count_event_tickets(admin_sb, event_id)
    pending_count = booking_service.count_pending_order_quantity(admin_sb, event_id)
    notified_count = _count_notified(admin_sb, event_id)
    if ticket_count + pending_count + notified_count < event_data["max_capacity"]:
        raise ValueError("event_not_full")

    # Check not already on waitlist (waiting or notified)
    existing_rows = (
        admin_sb.table("event_waitlist")
        .select("waitlist_id, status, joined_at")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .limit(1)
        .execute()
    )
    existing_data = existing_rows.data[0] if existing_rows.data else None
    if existing_data and existing_data["status"] in ("waiting", "notified"):
        raise ValueError("already_on_waitlist")

    now = datetime.now(timezone.utc).isoformat()

    if existing_data:
        # Re-joining after removal/expiry: reset with new joined_at (back of queue)
        user_sb.table("event_waitlist").update({
            "status": "waiting",
            "joined_at": now,
            "notified_at": None,
            "promotion_expires_at": None,
        }).eq("waitlist_id", existing_data["waitlist_id"]).execute()
        waitlist_id = existing_data["waitlist_id"]
    else:
        result = user_sb.table("event_waitlist").insert({
            "event_id": event_id,
            "person_id": person_id,
            "status": "waiting",
            "joined_at": now,
        }).execute()
        waitlist_id = result.data[0]["waitlist_id"]

    position = _get_position_count(admin_sb, event_id, now) + 1
    return {"waitlist_id": waitlist_id, "position": position}


def leave_waitlist(event_id: str, person_id: str, token: str) -> None:
    """Remove person from the event waitlist."""
    user_sb = get_supabase_for_user(token)
    existing_rows = (
        user_sb.table("event_waitlist")
        .select("waitlist_id, status")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .limit(1)
        .execute()
    )
    existing_data = existing_rows.data[0] if existing_rows.data else None
    if not existing_data or existing_data["status"] not in ("waiting", "notified"):
        raise ValueError("not_on_waitlist")
    user_sb.table("event_waitlist").update({"status": "removed"}).eq(
        "event_id", event_id
    ).eq("person_id", person_id).execute()


def get_waitlist_position(event_id: str, person_id: str, token: str) -> int:
    """Return 1-based position of person in the waitlist queue.
    Notified users are next up and return position 0."""
    user_sb = get_supabase_for_user(token)
    own_rows = (
        user_sb.table("event_waitlist")
        .select("joined_at, status")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .in_("status", ["waiting", "notified"])
        .limit(1)
        .execute()
    )
    own_data = own_rows.data[0] if own_rows.data else None
    if not own_data:
        raise ValueError("not_on_waitlist")
    if own_data.get("status") == "notified":
        return 0
    return _get_position_count(user_sb, event_id, own_data["joined_at"]) + 1


def get_waitlist_position_for_person(
    event_id: str, person_id: str, supabase
) -> int | None:
    """Return position using an existing supabase client. Returns None if not on waitlist.
    Notified users are next up and return position 0."""
    own_rows = (
        supabase.table("event_waitlist")
        .select("joined_at, status")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .in_("status", ["waiting", "notified"])
        .limit(1)
        .execute()
    )
    own_data = own_rows.data[0] if own_rows.data else None
    if not own_data:
        return None
    if own_data.get("status") == "notified":
        return 0
    return _get_position_count(supabase, event_id, own_data["joined_at"]) + 1


def expire_stale_promotions(event_id: str) -> int:
    """Set overdue 'notified' entries to 'expired'. Returns count of expired entries."""
    admin_sb = get_supabase_admin()
    now = datetime.now(timezone.utc).isoformat()
    stale = (
        admin_sb.table("event_waitlist")
        .select("waitlist_id")
        .eq("event_id", event_id)
        .eq("status", "notified")
        .lt("promotion_expires_at", now)
        .execute()
    )
    entries = stale.data or []
    for entry in entries:
        admin_sb.table("event_waitlist").update({"status": "expired"}).eq(
            "waitlist_id", entry["waitlist_id"]
        ).execute()
    return len(entries)


def promote_next(event_id: str) -> None:
    """Promote waiting people into the event until all free slots are filled or queue is empty.

    Free events: ticket created immediately, waitlist entry deleted.
    Paid events: status set to 'notified', deadline set, email sent. Stops after one (slot is soft-reserved).
    """
    expire_stale_promotions(event_id)
    admin_sb = get_supabase_admin()

    event_rows = (
        admin_sb.table("event")
        .select("max_capacity, is_free, waitlist_promotion_hours, title, invitation_link")
        .eq("event_id", event_id)
        .limit(1)
        .execute()
    )
    if not event_rows.data or not event_rows.data[0].get("max_capacity"):
        return

    event = event_rows.data[0]

    while True:
        ticket_count = booking_service.count_event_tickets(admin_sb, event_id)
        pending_count = booking_service.count_pending_order_quantity(admin_sb, event_id)
        notified_count = _count_notified(admin_sb, event_id)
        free_slots = event["max_capacity"] - ticket_count - pending_count - notified_count
        if free_slots <= 0:
            return

        next_entries = (
            admin_sb.table("event_waitlist")
            .select("waitlist_id, person_id")
            .eq("event_id", event_id)
            .eq("status", "waiting")
            .order("joined_at")
            .limit(1)
            .execute()
        )
        if not next_entries.data:
            return

        entry = next_entries.data[0]
        person_id = entry["person_id"]

        person_rows = (
            admin_sb.table("person")
            .select("first_name, last_name, email_address")
            .eq("person_id", person_id)
            .limit(1)
            .execute()
        )
        person = person_rows.data[0] if person_rows.data else {}
        guest_name = (
            f"{person.get('first_name', '')} {person.get('last_name', '') or ''}".strip()
            or "Gast"
        )

        if event.get("is_free", True):
            _promote_free(admin_sb, event_id, event, person_id, entry, guest_name, person)
        else:
            _promote_paid(admin_sb, event_id, event, person_id, entry, guest_name, person)
            return  # Paid promotion soft-reserves the slot; loop exits


def _promote_free(admin_sb, event_id, event, person_id, entry, guest_name, person):
    """Create a ticket immediately for a free-event waitlist member."""
    from app.core.ticket_token import generate_ticket_token
    from app.services.ticket_service import ensure_participation_accepted

    ensure_participation_accepted(admin_sb, event_id, person_id)
    qr_token = generate_ticket_token(event_id, guest_name, 1, None)
    admin_sb.table("ticket").insert({
        "event_id": event_id,
        "person_id": person_id,
        "qr_token": qr_token,
        "guest_name": guest_name,
    }).execute()
    admin_sb.table("event_waitlist").delete().eq(
        "waitlist_id", entry["waitlist_id"]
    ).execute()

    if person.get("email_address"):
        from app.services.email_service import send_waitlist_confirmation_email
        send_waitlist_confirmation_email(
            email=person["email_address"],
            name=guest_name,
            event_title=event["title"],
        )


def _promote_paid(admin_sb, event_id, event, person_id, entry, guest_name, person):
    """Notify a paid-event waitlist member and start their promotion window."""
    hours = event.get("waitlist_promotion_hours", 24)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

    admin_sb.table("event_waitlist").update({
        "status": "notified",
        "notified_at": datetime.now(timezone.utc).isoformat(),
        "promotion_expires_at": expires_at.isoformat(),
    }).eq("waitlist_id", entry["waitlist_id"]).execute()

    if person.get("email_address"):
        from app.services.email_service import send_waitlist_promotion_email
        send_waitlist_promotion_email(
            email=person["email_address"],
            name=guest_name,
            event_title=event["title"],
            event_link=event.get("invitation_link", ""),
            expires_at=expires_at,
        )
