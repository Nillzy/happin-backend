"""User account business logic — stats, events, tickets, account deletion."""

from datetime import datetime, timezone

from app.core.supabase import get_supabase, get_supabase_for_user


def get_user_stats(person_id: str) -> dict:
    supabase = get_supabase()

    # Events created (as host)
    hosted = (
        supabase.table("event_host")
        .select("event_id", count="exact")
        .eq("person_id", person_id)
        .execute()
    )
    events_created = hosted.count or 0

    # Participants across all hosted events
    hosted_event_ids = [row["event_id"] for row in (hosted.data or [])]
    participants_total = 0
    if hosted_event_ids:
        parts = (
            supabase.table("event_participation")
            .select("event_participation_id", count="exact")
            .in_("event_id", hosted_event_ids)
            .eq("status", "Accepted")
            .execute()
        )
        participants_total = parts.count or 0

    # Events attended (has participation, but is not the host)
    attended = (
        supabase.table("event_participation")
        .select("event_id", count="exact")
        .eq("person_id", person_id)
        .execute()
    )
    events_attended = attended.count or 0

    # Tickets = participations (no separate ticket purchase table yet)
    tickets_total = events_attended

    return {
        "events_attended": events_attended,
        "events_created": events_created,
        "tickets_total": tickets_total,
        "participants_total": participants_total,
    }


def get_user_events(
    person_id: str,
    role: str | None = None,
    period: str = "upcoming",
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    events: list[dict] = []

    if role in (None, "organizer"):
        # Events where user is host
        host_rows = (
            supabase.table("event_host")
            .select("event_id")
            .eq("person_id", person_id)
            .execute()
        )
        host_event_ids = [r["event_id"] for r in (host_rows.data or [])]

        if host_event_ids:
            query = (
                supabase.table("event")
                .select("*, location(*), event_media(media_url), event_host(person_id), event_participation(event_participation_id)")
                .in_("event_id", host_event_ids)
            )
            if period == "upcoming":
                query = query.gte("starts_at", now)
            else:
                query = query.lt("starts_at", now)

            result = query.order("starts_at", desc=(period == "past")).execute()
            for event in (result.data or []):
                event["is_host"] = True
            events.extend(result.data or [])

    if role in (None, "attendee"):
        # Events where user is a participant (not host)
        part_rows = (
            supabase.table("event_participation")
            .select("event_id")
            .eq("person_id", person_id)
            .execute()
        )
        attendee_event_ids = [r["event_id"] for r in (part_rows.data or [])]

        if attendee_event_ids:
            query = (
                supabase.table("event")
                .select("*, location(*), event_media(media_url), event_host(person_id), event_participation(event_participation_id)")
                .in_("event_id", attendee_event_ids)
            )
            if period == "upcoming":
                query = query.gte("starts_at", now)
            else:
                query = query.lt("starts_at", now)

            result = query.order("starts_at", desc=(period == "past")).execute()
            for event in (result.data or []):
                event["is_host"] = False
            events.extend(result.data or [])

    # Deduplicate (user can be both host and attendee edge case)
    seen: set[str] = set()
    unique: list[dict] = []
    for e in events:
        if e["event_id"] not in seen:
            seen.add(e["event_id"])
            unique.append(e)

    # Sort and paginate in Python (cross-role merge)
    reverse = period == "past"
    unique.sort(key=lambda e: e.get("starts_at", ""), reverse=reverse)
    return unique[offset: offset + limit]


def get_user_tickets(person_id: str) -> dict:
    """
    Returns participations as tickets (no separate ticket purchase table exists yet).
    Joins event and ticket_option for display data.
    """
    supabase = get_supabase()

    response = (
        supabase.table("event_participation")
        .select(
            "event_participation_id, status, created_at, "
            "event(event_id, title, ticket_option(ticket_option_id, name, price))"
        )
        .eq("person_id", person_id)
        .order("created_at", desc=True)
        .execute()
    )

    rows = response.data or []
    tickets = []
    for row in rows:
        event = row.get("event") or {}
        options = event.get("ticket_option") or []
        option = options[0] if options else {}
        tickets.append({
            "ticket_id": row["event_participation_id"],
            "event_id": event.get("event_id", ""),
            "event_title": event.get("title", ""),
            "ticket_option_name": option.get("name", "Standard"),
            "price": float(option.get("price", 0.0)),
            "currency": "EUR",
            "status": row.get("status", "active"),
            "purchased_at": row.get("created_at"),
        })

    return {"tickets": tickets, "total": len(tickets)}


def delete_user(supabase_user_id: str, token: str) -> None:
    """
    Deletes all user data then removes the Supabase Auth account.
    Order: participations → hosted events → person row → auth user.
    Hosted events cascade-delete their locations, media, and participations via FK.
    """
    sb_user = get_supabase_for_user(token)
    sb_admin = get_supabase()

    # Resolve person_id
    person_row = (
        sb_user.table("person")
        .select("person_id")
        .eq("supabase_user_id", supabase_user_id)
        .maybe_single()
        .execute()
    )
    if not (person_row and person_row.data):
        # No person record — only delete auth entry
        sb_admin.auth.admin.delete_user(supabase_user_id)
        return

    person_id = person_row.data["person_id"]

    # Remove participations (guest RSVPs)
    sb_user.table("event_participation").delete().eq("person_id", person_id).execute()

    # Remove hosted events (cascades location, media, participations of guests)
    host_rows = (
        sb_user.table("event_host")
        .select("event_id")
        .eq("person_id", person_id)
        .execute()
    )
    for row in (host_rows.data or []):
        sb_user.table("event").delete().eq("event_id", row["event_id"]).execute()

    # Remove person record
    sb_user.table("person").delete().eq("person_id", person_id).execute()

    # Delete Supabase Auth user (requires service role — use admin client)
    sb_admin.auth.admin.delete_user(supabase_user_id)
