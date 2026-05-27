"""Reminder business logic (Anforderung K4)."""

from app.core.supabase import get_supabase_admin, get_supabase_for_user

DEFAULT_LEAD_TIME_MINUTES = 60


def get_preference(person_id: str, token: str) -> dict:
    """Liefert die Reminder-Präferenz; falls keine existiert, Defaults."""
    sb = get_supabase_for_user(token)
    row = (
        sb.table("reminder_preference")
        .select("enabled, lead_time_minutes")
        .eq("person_id", person_id)
        .maybe_single()
        .execute()
    )
    if row and row.data:
        return row.data
    return {"enabled": False, "lead_time_minutes": DEFAULT_LEAD_TIME_MINUTES}


def upsert_preference(
    person_id: str,
    token: str,
    enabled: bool | None,
    lead_time_minutes: int | None,
) -> dict:
    sb = get_supabase_for_user(token)
    current = get_preference(person_id, token)
    new_enabled = enabled if enabled is not None else current["enabled"]
    new_lead = lead_time_minutes if lead_time_minutes is not None else current["lead_time_minutes"]

    sb.table("reminder_preference").upsert(
        {
            "person_id": person_id,
            "enabled": new_enabled,
            "lead_time_minutes": new_lead,
        },
        on_conflict="person_id",
    ).execute()
    return {"enabled": new_enabled, "lead_time_minutes": new_lead}


def upsert_subscription(
    person_id: str,
    token: str,  # noqa: ARG001 — Signatur stabil halten, Service nutzt Admin-Client
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str | None,
) -> None:
    """Speichert/aktualisiert eine Web-Push-Subscription.

    `endpoint` ist global unique (1 Browser = 1 Zeile). Beim Login eines
    anderen Users im selben Browser wird `person_id` per Upsert übertragen.
    Admin-Client ist nötig, weil die UPDATE-RLS-Policy am alten Owner hängt.
    """
    get_supabase_admin().table("web_push_subscription").upsert(
        {
            "person_id": person_id,
            "endpoint": endpoint,
            "p256dh_key": p256dh,
            "auth_key": auth,
            "user_agent": user_agent,
        },
        on_conflict="endpoint",
    ).execute()


def delete_subscription(person_id: str, token: str, endpoint: str) -> None:
    sb = get_supabase_for_user(token)
    sb.table("web_push_subscription").delete().eq("person_id", person_id).eq(
        "endpoint", endpoint
    ).execute()


def list_subscriptions(person_id: str, token: str) -> list[dict]:
    """Liefert alle Web-Push-Subscriptions des Users für die Geräte-Verwaltung.

    Gibt `endpoint` zurück (die UI braucht ihn, um das aktuelle Gerät zu
    markieren), aber NICHT die kryptographischen Keys.
    """
    sb = get_supabase_for_user(token)
    res = (
        sb.table("web_push_subscription")
        .select("web_push_subscription_id, endpoint, user_agent, created_at")
        .eq("person_id", person_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def delete_subscription_by_id(person_id: str, token: str, sub_id: str) -> bool:
    sb = get_supabase_for_user(token)
    res = (
        sb.table("web_push_subscription")
        .delete()
        .eq("person_id", person_id)
        .eq("web_push_subscription_id", sub_id)
        .execute()
    )
    return bool(res.data)
