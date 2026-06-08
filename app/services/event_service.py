"""Event-related business logic and Supabase queries."""

import logging
import secrets
from datetime import datetime, timezone, UTC, timedelta

from app.core.supabase import get_supabase, get_supabase_for_user, get_supabase_admin
from app.services import person_service, payment_service
from app.services.geocoding_service import geocode_address

logger = logging.getLogger(__name__)


def _isoformat(value) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _ensure_event_active(event_id: str, token: str) -> dict:
    """Fetch event and raise if cancelled or missing.

    Raises ValueError('event_not_found') if event does not exist.
    Raises ValueError('event_cancelled') if cancelled_at is set.
    Returns the event row dict on success.
    """
    supabase = get_supabase_for_user(token)
    row = (
        supabase.table("event")
        .select("event_id, cancelled_at")
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )
    if not row or not row.data:
        raise ValueError("event_not_found")
    if row.data.get("cancelled_at") is not None:
        raise ValueError("event_cancelled")
    return row.data


def _strip_location_for_privacy(event_data: dict, supabase_user_id: str | None) -> dict:
    """Strip location to city/country only if location_is_private and user hasn't accepted RSVP."""
    if not event_data.get("location_is_private"):
        return event_data
    if event_data.get("is_host"):
        return event_data
    participations = event_data.get("event_participation") or []
    user_accepted = any(
        p.get("status") == "Accepted"
        and (p.get("person") or {}).get("supabase_user_id") == supabase_user_id
        for p in participations
    )
    if user_accepted:
        return event_data
    loc = event_data.get("location")
    if loc:
        event_data["location"] = {
            "location_id": loc.get("location_id"),
            "city": loc.get("city"),
            "country": loc.get("country"),
        }
    return event_data


def get_public_events(
    limit: int = 50,
    offset: int = 0,
    person_id: str | None = None,
    token: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    categories: str | None = None,
    city: str | None = None,
    is_free: bool | None = None,
    search: str | None = None,
) -> tuple[list[dict], int]:
    """
    Get public events with optional filtering and pagination.
    Returns (events, total_count) tuple.

    Filters applied at DB level: date_from, date_to, is_free, search (title ilike).
    Filters applied in Python post-fetch: city, categories (comma-separated OR logic).
    """
    supabase = get_supabase_for_user(token) if token else get_supabase()
    supabase_admin = get_supabase_admin()
    lower_bound = date_from if date_from else datetime.now(UTC).isoformat()

    paid_event_ids_filter: list[str] = []
    if is_free is True:
        paid_filter_resp = (
            supabase_admin.table("ticket_option")
            .select("event_id")
            .gt("price", 0)
            .execute()
        )
        paid_event_ids_filter = list(
            {row["event_id"] for row in (paid_filter_resp.data or [])}
        )

    # Count query (same filters as paginated query, excluding pagination-only args)
    # ilike/filter with % sends raw % in the URL which triggers a Cloudflare Worker
    # exception (1101) on Supabase. or_() URL-encodes % as %25 and avoids this.
    search_term = search.strip() if search else None
    count_q = (
        supabase.table("event")
        .select("event_id", count="exact")
        .eq("is_public", True)
        .eq("status", "published")
        .gte("starts_at", lower_bound)
        .filter("cancelled_at", "is", "null")
    )
    if date_to:
        count_q = count_q.lte("starts_at", date_to)
    if is_free is True:
        count_q = count_q.eq("is_free", True)
        if paid_event_ids_filter:
            count_q = count_q.not_.in_("event_id", paid_event_ids_filter)
    if search_term:
        count_q = count_q.or_(f"title.ilike.%{search_term}%")
    count_response = count_q.execute()
    total_count = count_response.count if hasattr(count_response, "count") else 0

    # Paginated events query
    q = (
        supabase.table("event")
        .select(
            "*, location(*), event_media(media_url), "
            "event_host(person_id), "
            "ticket(ticket_id)"
        )
        .eq("is_public", True)
        .eq("status", "published")
        .gte("starts_at", lower_bound)
        .filter("cancelled_at", "is", "null")
    )
    if date_to:
        q = q.lte("starts_at", date_to)
    if is_free is True:
        q = q.eq("is_free", True)
        if paid_event_ids_filter:
            q = q.not_.in_("event_id", paid_event_ids_filter)
    if search_term:
        q = q.or_(f"title.ilike.%{search_term}%")
    q = q.order("starts_at", desc=False).range(offset, offset + limit - 1)
    response = q.execute()

    events = response.data if response.data else []
    if not events:
        return events, total_count

    # Preise aller Ticketoptionen für diese Events via Admin-Client laden (umgeht RLS)
    event_ids = [e["event_id"] for e in events]
    opts_response = supabase_admin.table("ticket_option").select("event_id, price").in_("event_id", event_ids).execute()
    paid_event_ids = {
        row["event_id"]
        for row in (opts_response.data or [])
        if float(row.get("price", 0)) > 0
    }

    # Python post-fetch: city filter (case-insensitive)
    if city:
        city_lower = city.strip().lower()
        events = [
            e for e in events
            if (e.get("location") or {}).get("city", "").lower() == city_lower
        ]

    # Python post-fetch: category filter (OR logic, partial match)
    if categories:
        cats = [c.strip().lower() for c in categories.split(",") if c.strip()]
        if cats:
            events = [
                e for e in events
                if any(
                    cat in (e.get("category") or "").lower()
                    for cat in cats
                )
            ]

    for event in events:
        if person_id:
            event["is_host"] = any(
                h.get("person_id") == person_id
                for h in event.get("event_host", [])
            )
        else:
            event["is_host"] = False
        if event["event_id"] in paid_event_ids:
            event["is_free"] = False
        # For list view, participation data is not fetched, so non-hosts never have accepted RSVP
        _strip_location_for_privacy(event, None)

    return events, total_count

def get_public_events_by_host(host_person_id: str, limit: int = 50, offset: int = 0, token: str | None = None) -> tuple[list[dict], int]:
    """Get all public events organized by a specific host."""
    supabase = get_supabase_for_user(token) if token else get_supabase()
    supabase_admin = get_supabase_admin()
    lower_bound = datetime.now(UTC).isoformat()

    # Count query
    count_q = (
        supabase.table("event")
        .select("event_id, event_host!inner(person_id)", count="exact")
        .eq("is_public", True)
        .eq("status", "published")
        .eq("event_host.person_id", host_person_id)
        .gte("starts_at", lower_bound)
        .filter("cancelled_at", "is", "null")
    )
    count_response = count_q.execute()
    total_count = count_response.count if hasattr(count_response, "count") else 0

    # Paginated events query
    q = (
        supabase.table("event")
        .select(
            "*, location(*), event_media(media_url), "
            "event_host!inner(person_id), "
            "ticket(ticket_id)"
        )
        .eq("is_public", True)
        .eq("status", "published")
        .eq("event_host.person_id", host_person_id)
        .gte("starts_at", lower_bound)
        .filter("cancelled_at", "is", "null")
        .order("starts_at", desc=False)
        .range(offset, offset + limit - 1)
    )
    response = q.execute()

    events = response.data if response.data else []
    if not events:
        return events, total_count

    # Load ticket prices for is_free determination
    event_ids = [e["event_id"] for e in events]
    opts_response = supabase_admin.table("ticket_option").select("event_id, price").in_("event_id", event_ids).execute()
    paid_event_ids = {
        row["event_id"]
        for row in (opts_response.data or [])
        if float(row.get("price", 0)) > 0
    }

    for event in events:
        event["is_host"] = True  # All events in this list are hosted by the requested person
        if event["event_id"] in paid_event_ids:
            event["is_free"] = False
        _strip_location_for_privacy(event, None)

    return events, total_count

def get_public_events_count() -> int:
    supabase = get_supabase()

    response = (
        supabase.table("event")
        .select("*", count="exact")
        .eq("is_public", True)
        .eq("status", "published")
        .gte("starts_at", datetime.now(UTC).isoformat())
        .filter("cancelled_at", "is", "null")
        .execute()
    )

    return response.count or 0


def get_event_by_id(event_id: str, supabase_user_id: str | None = None, token: str | None = None) -> dict | None:
    # Authenticated requests use the user token (RLS as that user).
    # Unauthenticated requests use the admin client to bypass RLS;
    # guest-visibility restrictions are then enforced in the API layer.
    if token:
        supabase = get_supabase_for_user(token)
    else:
        from app.core.supabase import get_supabase_admin
        supabase = get_supabase_admin()

    response = (
        supabase.table("event")
        .select(
            "*, location(*), event_media(media_url), ticket_option(*), "
            "event_host(person(person_id, supabase_user_id, first_name, last_name)), "
            "event_participation(event_participation_id, status, person(person_id, supabase_user_id)), "
            "ticket(ticket_id, person_id, guest_name), custom_field(*)"
        )
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )

    if not response or not response.data:
        return None

    data = response.data

    my_person_id = None
    if supabase_user_id:
        participations = data.get("event_participation") or []
        my_participation = next(
            (p for p in participations
             if p.get("person", {}).get("supabase_user_id") == supabase_user_id),
            None,
        )
        data["my_rsvp_status"] = my_participation["status"] if my_participation else None

        hosts = data.get("event_host") or []
        data["is_host"] = any(
            h.get("person", {}).get("supabase_user_id") == supabase_user_id
            for h in hosts
        )

        person_row = (
            supabase.table("person")
            .select("person_id")
            .eq("supabase_user_id", supabase_user_id)
            .maybe_single()
            .execute()
        )
        person_data = getattr(person_row, "data", None) if person_row else None
        if person_data:
            my_person_id = person_data["person_id"]
        all_tickets = data.get("ticket") or []
        data["my_tickets"] = [
            {"ticket_id": t["ticket_id"], "guest_name": t.get("guest_name")}
            for t in all_tickets
            if t.get("person_id") == my_person_id
        ] if my_person_id else []
    else:
        data["my_rsvp_status"] = None
        data["is_host"] = False
        data["my_tickets"] = []

    # Wenn mind. eine Ticketoption mit Preis > 0 existiert, ist das Event nicht kostenlos
    ticket_options = data.get("ticket_option") or []
    if any(float(t.get("price", 0)) > 0 for t in ticket_options):
        data["is_free"] = False

    _strip_location_for_privacy(data, supabase_user_id)

    # Compute is_full: checks tickets + pending orders + notified waitlist entries vs max_capacity
    max_cap = data.get("max_capacity")
    if max_cap:
        try:
            from app.services.waitlist_service import (
                expire_stale_promotions,
                _count_notified,
                get_waitlist_position_for_person,
            )
            from app.core.supabase import get_supabase_admin
            from app.services import booking_service as _bs
            expire_stale_promotions(event_id)
            _admin = get_supabase_admin()
            t_count = int(_bs.count_event_tickets(_admin, event_id) or 0)
            p_count = int(_bs.count_pending_order_quantity(_admin, event_id) or 0)
            n_count = int(_count_notified(_admin, event_id) or 0)
            data["is_full"] = (t_count + p_count + n_count) >= int(max_cap)
            data["my_waitlist_position"] = (
                get_waitlist_position_for_person(event_id, my_person_id, _admin)
                if my_person_id else None
            )
        except Exception:
            logger.exception("Failed to compute waitlist fields for event %s", event_id)
            data["is_full"] = False
            data["my_waitlist_position"] = None
    else:
        data["is_full"] = False
        data["my_waitlist_position"] = None

    return data


def create_event(data: dict, person_id: str, token: str, supabase_user_id: str | None = None) -> dict:
    supabase = get_supabase_for_user(token)

    location_data = data.pop("location")
    location_insert = {k: v for k, v in location_data.items() if v is not None}
    location_resp = (
        supabase.table("location")
        .insert(location_insert)
        .execute()
    )
    location_id = location_resp.data[0]["location_id"]

    coords = None
    if location_data.get("latitude") is None or location_data.get("longitude") is None:
        coords = geocode_address(
            street=location_data.get("street"),
            house_number=location_data.get("house_number"),
            postal_code=location_data.get("postal_code"),
            city=location_data.get("city"),
            country=location_data.get("country"),
        )
    if coords:
        supabase.table("location").update({
            "latitude": coords[0],
            "longitude": coords[1],
        }).eq("location_id", location_id).execute()

    invitation_link = secrets.token_urlsafe(16)

    event_payload = {
        "title": data["title"],
        "starts_at": _isoformat(data["starts_at"]),
        "description": data.get("description"),
        "category": data.get("category"),
        "max_capacity": data.get("max_capacity"),
        "max_tickets_per_person": data.get("max_tickets_per_person"),
        "is_public": data["is_public"],
        "is_free": data.get("is_free", True),
        "status": data.get("status", "published"),
        "location_id": location_id,
        "invitation_link": invitation_link,
        "location_is_private": data.get("location_is_private", False),
    }
    if data.get("ends_at"):
        event_payload["ends_at"] = _isoformat(data["ends_at"])
    if data.get("gradient_id") is not None:
        event_payload["gradient_id"] = data["gradient_id"]

    event_payload["payout_person_id"] = person_id

    event_resp = (
        supabase.table("event")
        .insert(event_payload)
        .execute()
    )
    event_id = event_resp.data[0]["event_id"]

    supabase.table("event_host").insert({
        "person_id": person_id,
        "event_id": event_id,
    }).execute()

    image_url = data.get("image_url")
    if image_url:
        supabase.table("event_media").insert({
            "event_id": event_id,
            "media_url": image_url,
        }).execute()

    return get_event_by_id(event_id, supabase_user_id=supabase_user_id, token=token)


def update_event(event_id: str, data: dict, person_id: str, token: str, supabase_user_id: str | None = None) -> dict | None:
    """Update an existing event. Only the host may update."""
    _ensure_event_active(event_id, token)
    supabase = get_supabase_for_user(token)

    host_entry = (
        supabase.table("event_host")
        .select("event_host_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .maybe_single()
        .execute()
    )
    if not host_entry.data:
        return None

    # Felder, die der Caller explizit ändern wollte — Basis für die Notification-Diff.
    # `location` und `image_url`/`media_urls` werden auf "location" bzw. "media" verdichtet.
    changed_fields: list[str] = []
    for key in data.keys():
        if key == "location":
            changed_fields.append("location")
        elif key in ("image_url", "media_urls"):
            if "media" not in changed_fields:
                changed_fields.append("media")
        else:
            changed_fields.append(key)

    location_data = data.pop("location", None)
    if location_data:
        event_row = (
            supabase.table("event")
            .select("location_id")
            .eq("event_id", event_id)
            .single()
            .execute()
        )
        location_id = event_row.data["location_id"]
        has_coords = location_data.get("latitude") is not None and location_data.get("longitude") is not None
        # city allein gilt nicht als vollständige Adresse — nur Straße/PLZ/Land zählen
        has_address = any(location_data.get(f) for f in ("street", "house_number", "postal_code", "country"))
        if has_coords and not has_address:
            # Koordinaten-Ort (ggf. mit Stadt): alte Adressfelder löschen
            loc_patch = {
                "latitude": location_data["latitude"],
                "longitude": location_data["longitude"],
                "city": location_data.get("city"),
                "street": None,
                "house_number": None,
                "postal_code": None,
                "country": None,
            }
        else:
            loc_patch = {k: v for k, v in location_data.items() if v is not None}
            # Koordinaten aus Adresse ermitteln, falls nicht mitgeschickt
            if not has_coords:
                coords = geocode_address(
                    street=location_data.get("street"),
                    house_number=location_data.get("house_number"),
                    postal_code=location_data.get("postal_code"),
                    city=location_data.get("city"),
                    country=location_data.get("country"),
                )
                if coords:
                    loc_patch["latitude"] = coords[0]
                    loc_patch["longitude"] = coords[1]
        if loc_patch:
            supabase.table("location").update(loc_patch).eq("location_id", location_id).execute()

    has_image_url_field = "image_url" in data
    image_url = data.pop("image_url", None)
    media_urls = data.pop("media_urls", None)  # None = not provided, [] = clear all

    if media_urls is not None:
        # Sync event_media rows using the user-scoped client (respects RLS)
        existing_media = (
            supabase.table("event_media")
            .select("media_id, media_url")
            .eq("event_id", event_id)
            .order("media_id")
            .execute()
        )
        existing_rows = existing_media.data or []

        # Update existing rows in-place, insert new ones, delete surplus
        for i, url in enumerate(media_urls):
            if i < len(existing_rows):
                supabase.table("event_media").update({"media_url": url}).eq(
                    "media_id", existing_rows[i]["media_id"]
                ).execute()
            else:
                supabase.table("event_media").insert(
                    {"event_id": event_id, "media_url": url}
                ).execute()

        # Delete any surplus rows beyond the new list length
        for row in existing_rows[len(media_urls):]:
            supabase.table("event_media").delete().eq(
                "media_id", row["media_id"]
            ).execute()
    elif has_image_url_field:
        # Only the cover image changed — update/insert/delete the first media entry
        existing_media = (
            supabase.table("event_media")
            .select("media_id")
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )
        if image_url:
            if existing_media.data:
                supabase.table("event_media").update({
                    "media_url": image_url,
                }).eq("media_id", existing_media.data[0]["media_id"]).execute()
            else:
                supabase.table("event_media").insert({
                    "event_id": event_id,
                    "media_url": image_url,
                }).execute()
        elif existing_media.data:
            supabase.table("event_media").delete().eq(
                "media_id", existing_media.data[0]["media_id"]
            ).execute()

    event_patch = {}
    for key, value in data.items():
        event_patch[key] = _isoformat(value) if hasattr(value, "isoformat") else value

    if event_patch:
        if data.get("is_public") is True:
            payment_service.require_stripe_for_paid_public_event(event_id, is_public=True)
        elif data.get("status") == "published":
            payment_service.require_stripe_for_paid_public_event(event_id)

        supabase.table("event").update(event_patch).eq("event_id", event_id).execute()

    if data.get("is_free") is True:
        supabase.table("ticket_option").delete().eq("event_id", event_id).execute()

    if changed_fields:
        try:
            from app.services import notification_service
            notification_service.fanout_event_updated(event_id, changed_fields)
        except Exception:
            # Notification-Fehler dürfen das Update nicht killen
            import logging
            logging.getLogger(__name__).exception("[notifications] fanout_event_updated fehlgeschlagen")

    return get_event_by_id(event_id, supabase_user_id=supabase_user_id, token=token)


def rsvp_event(event_id: str, supabase_user_id: str, email: str | None, status: str, token: str) -> dict:
    """Create or update a guest RSVP for an event."""
    logging.getLogger(__name__).warning(
        "[rsvp] ENTER rsvp_event event=%s status=%s user=%s",
        event_id, status, supabase_user_id,
    )
    _ensure_event_active(event_id, token)
    supabase = get_supabase_for_user(token)

    person = person_service.get_or_create_person(supabase_user_id, email, token)
    person_id = person["person_id"]

    event_row = (
        supabase.table("event")
        .select("starts_at, is_public")
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )
    if not event_row.data:
        raise ValueError("event_not_found")

    starts_at_str = event_row.data["starts_at"]
    starts_at = datetime.fromisoformat(starts_at_str.replace("Z", "+00:00"))
    if starts_at <= datetime.now(timezone.utc):
        raise ValueError("event_in_past")

    if event_row.data["is_public"] and status == "Pending":
        raise ValueError("public_event_accepted_only")

    # Vor-Status snapshotten — bestimmt, ob bei 'Accepted' eine Notification an den Host fällig ist.
    prev_participation = (
        supabase.table("event_participation")
        .select("status")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .maybe_single()
        .execute()
    )
    prev_status = (prev_participation.data or {}).get("status") if prev_participation else None

    result = supabase.rpc("rsvp_to_event", {
        "p_event_id": event_id,
        "p_person_id": person_id,
        "p_status": status,
    }).execute()

    rpc_data = result.data
    if isinstance(rpc_data, dict) and rpc_data.get("error"):
        raise ValueError(rpc_data["error"])

    participation = (
        supabase.table("event_participation")
        .select("event_participation_id, event_id, person_id, status")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .single()
        .execute()
    )

    if participation.data and participation.data.get("status") == "Accepted" and prev_status != "Accepted":
        try:
            from app.services import notification_service
            logging.getLogger(__name__).info(
                "[rsvp] Trigger fanout_new_participant: event=%s person=%s prev=%s",
                event_id, person_id, prev_status,
            )
            notification_service.fanout_new_participant(event_id, person_id)
        except Exception:
            logging.getLogger(__name__).exception("[notifications] fanout_new_participant fehlgeschlagen")
    elif participation.data and participation.data.get("status") == "Declined" and prev_status == "Accepted":
        try:
            from app.services import notification_service
            logging.getLogger(__name__).info(
                "[rsvp] Trigger fanout_participant_cancelled: event=%s person=%s",
                event_id, person_id,
            )
            notification_service.fanout_participant_cancelled(event_id, person_id)
        except Exception:
            logging.getLogger(__name__).exception("[notifications] fanout_participant_cancelled fehlgeschlagen")
    else:
        logging.getLogger(__name__).info(
            "[rsvp] Kein Fanout: status=%s prev_status=%s",
            (participation.data or {}).get("status"), prev_status,
        )

    return participation.data


def is_user_host(event_id: str, person_id: str) -> bool:
    """Check if a person is the host of an event."""
    supabase = get_supabase()

    response = (
        supabase.table("event_host")
        .select("event_host_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .maybe_single()
        .execute()
    )

    return response is not None and response.data is not None


def get_event_participants(event_id: str, token: str) -> dict:
    """Get all participants for an event with counts by status."""
    supabase = get_supabase_for_user(token)

    response = (
        supabase.table("event_participation")
        .select(
            "event_participation_id, status, created_at, "
            "person(person_id, first_name, last_name, phone_number)"
        )
        .eq("event_id", event_id)
        .execute()
    )

    participants = response.data if response.data else []

    ticket_response = (
        supabase.table("ticket")
        .select("ticket_id, person_id, guest_name, custom_field_response(custom_field_id, value), ticket_option(ticket_option_id, name, price)")
        .eq("event_id", event_id)
        .execute()
    )
    tickets = ticket_response.data or []

    # Per-person: total count + breakdown by option
    ticket_counts_by_person: dict[str, int] = {}
    responses_by_person: dict[str, list] = {}
    ticket_options_by_person: dict[str, dict[str, int]] = {}  # person_id → {option_name → count}
    option_summary: dict[str, dict] = {}  # option_name → {count, price}

    for t in tickets:
        pid = t["person_id"]
        opt = t.get("ticket_option") or {}
        opt_name = opt.get("name") or "Standard"
        opt_price = float(opt.get("price", 0))

        ticket_counts_by_person[pid] = ticket_counts_by_person.get(pid, 0) + 1
        if pid not in responses_by_person:
            responses_by_person[pid] = []
        responses_by_person[pid].append({
            "ticket_id": t["ticket_id"],
            "guest_name": t.get("guest_name"),
            "ticket_option_id": opt.get("ticket_option_id"),
            "ticket_option_name": opt_name,
            "responses": t.get("custom_field_response") or [],
        })

        if pid not in ticket_options_by_person:
            ticket_options_by_person[pid] = {}
        ticket_options_by_person[pid][opt_name] = ticket_options_by_person[pid].get(opt_name, 0) + 1

        if opt_name not in option_summary:
            option_summary[opt_name] = {"name": opt_name, "price": opt_price, "sold": 0}
        option_summary[opt_name]["sold"] += 1

    counts = {"accepted": len(tickets), "declined": 0, "pending": 0}
    for p in participants:
        status = p.get("status", "").lower()
        if status == "declined":
            counts["declined"] += 1
        elif status == "pending":
            counts["pending"] += 1
        person_id = p.get("person", {}).get("person_id")
        if person_id:
            p["ticket_count"] = ticket_counts_by_person.get(person_id, 0)
            p["ticket_responses"] = responses_by_person.get(person_id, [])
            p["ticket_options_bought"] = ticket_options_by_person.get(person_id, {})
        else:
            p["ticket_count"] = 0
            p["ticket_responses"] = []
            p["ticket_options_bought"] = {}

    return {
        "participants": participants,
        "counts": counts,
        "ticket_option_summary": list(option_summary.values()),
    }


def remove_participants(event_id: str, participation_ids: list[str], token: str | None = None) -> int:
    """Remove participants from an event. Does not remove hosts.
    Requires a user token — RLS policy ensures only hosts can delete."""
    if token:
        client = get_supabase_for_user(token)
    else:
        client = get_supabase()

    participations = (
        client.table("event_participation")
        .select("event_participation_id, person_id")
        .eq("event_id", event_id)
        .in_("event_participation_id", participation_ids)
        .execute()
    )
    person_ids = [p["person_id"] for p in (participations.data or [])]

    response = (
        client.table("event_participation")
        .delete()
        .eq("event_id", event_id)
        .in_("event_participation_id", participation_ids)
        .execute()
    )

    for pid in person_ids:
        client.table("ticket").delete().eq("event_id", event_id).eq("person_id", pid).execute()

    return len(response.data) if response.data else 0


def _refund_all_paid_orders(event_id: str) -> "RefundSummary":
    """Refund every paid ticket_order for the event, mark pending orders as failed.

    Skips orders where every associated ticket has been scanned already.
    Stripe failures are logged but do not abort — they appear in failed_order_ids.
    """
    from app.schemas.events import RefundSummary
    from app.services import payment_service

    supabase = get_supabase()

    paid_orders = (
        supabase.table("ticket_order")
        .select("ticket_order_id, event_id, person_id, amount_total_cents, stripe_payment_intent_id, ticket_option_id")
        .eq("event_id", event_id)
        .eq("status", "paid")
        .execute()
    )

    refunded_count = 0
    failed_count = 0
    failed_order_ids: list[str] = []
    skipped_count = 0

    for order in paid_orders.data or []:
        order_tickets = (
            supabase.table("ticket")
            .select("ticket_id, scanned_at")
            .eq("ticket_order_id", order["ticket_order_id"])
            .execute()
        )
        tickets = order_tickets.data or []
        if tickets and all(t.get("scanned_at") for t in tickets):
            skipped_count += 1
            continue

        result = payment_service._refund_single_order(
            order,
            idempotency_key=f"event-cancel-{order['ticket_order_id']}",
        )
        if result["refunded"]:
            refunded_count += 1
        else:
            failed_count += 1
            failed_order_ids.append(order["ticket_order_id"])

    supabase.table("ticket_order").update({"status": "failed"}).eq(
        "event_id", event_id
    ).eq("status", "pending").execute()

    return RefundSummary(
        refunded_count=refunded_count,
        failed_count=failed_count,
        failed_order_ids=failed_order_ids,
        skipped_count=skipped_count,
    )


def cancel_event(event_id: str, person_id: str, token: str) -> "RefundSummary":
    """Cancel an event by setting cancelled_at = now() and refunding paid tickets.

    Raises PermissionError if caller is not the host.
    Raises ValueError('event_not_found') if event does not exist.
    Raises ValueError('already_cancelled') if event is already cancelled.
    Returns RefundSummary with refund counts.
    """
    supabase = get_supabase_for_user(token)

    host_entry = (
        supabase.table("event_host")
        .select("event_host_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .maybe_single()
        .execute()
    )
    if not host_entry.data:
        raise PermissionError("not_host")

    event_row = (
        supabase.table("event")
        .select("cancelled_at")
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )
    if not event_row.data:
        raise ValueError("event_not_found")

    if event_row.data.get("cancelled_at") is not None:
        raise ValueError("already_cancelled")

    supabase.table("event").update(
        {"cancelled_at": datetime.now(UTC).isoformat()}
    ).eq("event_id", event_id).execute()

    try:
        from app.services import notification_service
        notification_service.fanout_event_cancelled(event_id)
    except Exception:
        logger.exception("[notifications] fanout_event_cancelled fehlgeschlagen")

    return _refund_all_paid_orders(event_id)
