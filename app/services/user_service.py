"""User account business logic — stats, events, tickets, account deletion."""

from datetime import datetime, timezone, timedelta

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
    token: str,
    role: str | None = None,
    period: str = "upcoming",
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    supabase = get_supabase_for_user(token)
    now = datetime.now(timezone.utc).isoformat()
    delete_cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

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
                .select("*, location(*), event_media(media_url), event_host(person_id), ticket(ticket_id, ticket_option(price)), event_participation(status)")
                .in_("event_id", host_event_ids)
                .or_(f"deleted_at.is.null,deleted_at.gt.{delete_cutoff}")
            )
            if period == "upcoming":
                query = query.gte("starts_at", now)
            else:
                query = query.lt("starts_at", now)

            result = query.order("starts_at", desc=(period == "past")).execute()

            # Batch-load ticket_option prices to correctly flag paid events
            result_event_ids = [e["event_id"] for e in (result.data or [])]
            paid_event_ids: set[str] = set()
            if result_event_ids:
                opts_rows = (
                    supabase.table("ticket_option")
                    .select("event_id, price")
                    .in_("event_id", result_event_ids)
                    .execute()
                )
                paid_event_ids = {
                    r["event_id"] for r in (opts_rows.data or [])
                    if float(r.get("price", 0)) > 0
                }

            for event in (result.data or []):
                event["is_host"] = True
                # Umsatz berechnen: Summe aller verkauften Tickets × Preis
                tickets_sold = event.get("ticket", []) or []
                revenue_cents = sum(
                    int(float((t.get("ticket_option") or {}).get("price", 0)) * 100)
                    for t in tickets_sold
                    if t.get("ticket_option")
                )
                event["ticket_revenue_cents"] = revenue_cents
                if event["event_id"] in paid_event_ids:
                    event["is_free"] = False
            events.extend(result.data or [])

    if role in (None, "attendee"):
        # Events where user is a participant (not host) — only accepted
        part_rows = (
            supabase.table("event_participation")
            .select("event_id")
            .eq("person_id", person_id)
            .eq("status", "Accepted")
            .execute()
        )
        attendee_event_ids = [r["event_id"] for r in (part_rows.data or [])]

        if attendee_event_ids:
            query = (
                supabase.table("event")
                .select("*, location(*), event_media(media_url), event_host(person_id), ticket(ticket_id, ticket_option(price))")
                .in_("event_id", attendee_event_ids)
                .or_(f"deleted_at.is.null,deleted_at.gt.{delete_cutoff}")
            )
            if period == "upcoming":
                query = query.gte("starts_at", now)
            else:
                query = query.lt("starts_at", now)

            result = query.order("starts_at", desc=(period == "past")).execute()
            for event in (result.data or []):
                event["is_host"] = False
                tickets = event.get("ticket") or []
                if any(
                    float((t.get("ticket_option") or {}).get("price", 0)) > 0
                    for t in tickets
                ):
                    event["is_free"] = False
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


def get_user_tickets(person_id: str, token: str) -> dict:
    """Returns tickets from the ticket table with event and option details."""
    from app.services import ticket_service
    return ticket_service.get_tickets_for_person(person_id, token)


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
