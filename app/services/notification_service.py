"""Notification-Service: In-App-Benachrichtigungen + Web-Push-Fanout.

Erzeugt `notification`-Datensätze pro Empfänger, sendet zusätzlich Web-Push
an alle registrierten Subscriptions (Best-Effort — schlägt der Push fehl,
bleibt der In-App-Verlauf trotzdem bestehen).
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.supabase import get_supabase_admin, get_supabase_for_user

logger = logging.getLogger(__name__)

NOTIFICATION_TYPES = ("event_updated", "event_cancelled", "new_participant", "participant_cancelled")
# Felder, deren Änderung als "wesentlich" gilt — nur diese lösen Push aus.
# Alle Diff-Felder werden trotzdem im In-App-Verlauf gezeigt.
_PUSH_TRIGGER_FIELDS = {"title", "starts_at", "ends_at", "location"}


# ───────────────────────────── Empfänger-Auflösung ─────────────────────────────


def _accepted_participant_person_ids(db, event_id: str) -> list[str]:
    rows = (
        db.table("event_participation")
        .select("person_id")
        .eq("event_id", event_id)
        .eq("status", "Accepted")
        .execute()
        .data
        or []
    )
    return [r["person_id"] for r in rows if r.get("person_id")]


def _host_person_ids(db, event_id: str) -> list[str]:
    rows = (
        db.table("event_host")
        .select("person_id")
        .eq("event_id", event_id)
        .execute()
        .data
        or []
    )
    return [r["person_id"] for r in rows if r.get("person_id")]


def _event_title(db, event_id: str) -> str | None:
    row = (
        db.table("event")
        .select("title")
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )
    return row.data.get("title") if row and row.data else None


# ───────────────────────────── Insert + Push ─────────────────────────────


def _insert_notifications(db, recipient_ids: list[str], type_: str, event_id: str | None, payload: dict[str, Any]) -> None:
    if not recipient_ids:
        return
    rows = [
        {
            "recipient_person_id": pid,
            "event_id": event_id,
            "type": type_,
            "payload": payload,
        }
        for pid in recipient_ids
    ]
    try:
        db.table("notification").insert(rows).execute()
    except Exception as exc:  # pragma: no cover
        logger.warning("[notifications] Insert fehlgeschlagen: %s", exc)


def _push_to_recipients(db, recipient_ids: list[str], title: str, body: str, data: dict[str, Any]) -> None:
    """Best-Effort Push an alle Empfänger — Web (VAPID) + Native (Expo)."""
    if not recipient_ids:
        return

    # ── Web Push ──────────────────────────────────────────────────────────
    try:
        from app.services.reminder_scheduler import _send_push  # type: ignore
    except Exception as exc:  # pragma: no cover
        logger.info("[notifications] Push-Helper nicht verfügbar: %s", exc)
        _send_push = None  # type: ignore

    try:
        subs = (
            db.table("web_push_subscription")
            .select("person_id, endpoint, p256dh_key, auth_key")
            .in_("person_id", recipient_ids)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[notifications] Subs-Fetch fehlgeschlagen: %s", exc)
        subs = []

    logger.info(
        "[notifications] Push fanout: recipients=%d web_subs=%d type=%s",
        len(recipient_ids),
        len(subs),
        data.get("type"),
    )
    for sub in subs:
        endpoint = sub.get("endpoint", "")
        host = endpoint.split("/")[2] if "://" in endpoint else endpoint[:40]
        logger.info(
            "[notifications]   web sub person=%s host=%s ep=...%s",
            sub.get("person_id"), host, endpoint[-20:],
        )
    payload = {"title": title, "body": body, **data}
    web_success = 0
    if _send_push:
        for sub in subs:
            try:
                ok = _send_push(sub["endpoint"], sub["p256dh_key"], sub["auth_key"], payload)
                if ok:
                    web_success += 1
            except Exception as exc:  # pragma: no cover
                logger.warning("[notifications] Web-Push fehlgeschlagen: %s", exc)

    # ── Expo Push (Native iOS/Android) ────────────────────────────────────
    try:
        rows = (
            db.table("expo_push_token")
            .select("person_id, token, platform")
            .in_("person_id", recipient_ids)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[notifications] Expo-Token-Fetch fehlgeschlagen: %s", exc)
        rows = []

    expo_tokens = [r["token"] for r in rows if r.get("token")]
    expo_success = 0
    if expo_tokens:
        for r in rows:
            tk = r.get("token", "")
            logger.info(
                "[notifications]   expo token person=%s platform=%s tk=%s...%s",
                r.get("person_id"), r.get("platform"), tk[:18], tk[-6:],
            )
        try:
            from app.services import expo_push_service
            expo_success = expo_push_service.send_to_tokens(expo_tokens, title, body, data)
        except Exception as exc:  # pragma: no cover
            logger.warning("[notifications] Expo-Push-Send fehlgeschlagen: %s", exc)

    logger.info(
        "[notifications] Push fanout result: web=%d/%d expo=%d/%d",
        web_success, len(subs), expo_success, len(expo_tokens),
    )


# ───────────────────────────── Fanout-API ─────────────────────────────


def fanout_event_updated(event_id: str, changed_fields: list[str]) -> None:
    """Benachrichtigt alle akzeptierten Teilnehmer über eine Event-Änderung.

    `changed_fields` landet im payload. Nur Änderungen an wesentlichen Feldern
    (Titel/Zeit/Ort) lösen zusätzlich Web-Push aus; im In-App-Verlauf erscheinen
    sie alle.
    """
    if not changed_fields:
        return
    db = get_supabase_admin()
    recipients = _accepted_participant_person_ids(db, event_id)
    if not recipients:
        return
    title = _event_title(db, event_id) or "Event"
    payload = {"event_title": title, "changed_fields": changed_fields}
    _insert_notifications(db, recipients, "event_updated", event_id, payload)

    if _PUSH_TRIGGER_FIELDS.intersection(changed_fields):
        _push_to_recipients(
            db,
            recipients,
            title=title,
            body="Event wurde aktualisiert.",
            data={"type": "event_updated", "eventId": event_id},
        )


def fanout_event_cancelled(event_id: str) -> None:
    """Benachrichtigt alle akzeptierten Teilnehmer, dass das Event abgesagt wurde."""
    db = get_supabase_admin()
    recipients = _accepted_participant_person_ids(db, event_id)
    if not recipients:
        return
    title = _event_title(db, event_id) or "Event"
    payload = {"event_title": title}
    _insert_notifications(db, recipients, "event_cancelled", event_id, payload)
    _push_to_recipients(
        db,
        recipients,
        title=title,
        body="Event wurde abgesagt.",
        data={"type": "event_cancelled", "eventId": event_id},
    )


def fanout_new_participant(event_id: str, new_person_id: str) -> None:
    """Benachrichtigt Hosts über einen neuen akzeptierten Teilnehmer."""
    db = get_supabase_admin()
    hosts = _host_person_ids(db, event_id)
    # Host meldet sich nicht selbst — falls der Host gleichzeitig RSVPt
    recipients = [h for h in hosts if h != new_person_id]
    logger.info(
        "[notifications] new_participant fanout: event=%s hosts=%d recipients=%d new_person=%s",
        event_id, len(hosts), len(recipients), new_person_id,
    )
    if not recipients:
        return

    person_row = (
        db.table("person")
        .select("first_name, last_name")
        .eq("person_id", new_person_id)
        .maybe_single()
        .execute()
    )
    person_data = (person_row.data if person_row else None) or {}
    first = person_data.get("first_name") or ""
    last = person_data.get("last_name") or ""
    full_name = (first + " " + last).strip() or "Jemand"

    title = _event_title(db, event_id) or "Event"
    payload = {"event_title": title, "participant_name": full_name}
    _insert_notifications(db, recipients, "new_participant", event_id, payload)
    _push_to_recipients(
        db,
        recipients,
        title=title,
        body=f"{full_name} hat zugesagt.",
        data={"type": "new_participant", "eventId": event_id},
    )


def fanout_participant_cancelled(event_id: str, person_id: str) -> None:
    """Benachrichtigt Hosts, wenn ein Teilnehmer seine Zusage zurückzieht."""
    db = get_supabase_admin()
    hosts = _host_person_ids(db, event_id)
    recipients = [h for h in hosts if h != person_id]
    logger.info(
        "[notifications] participant_cancelled fanout: event=%s hosts=%d recipients=%d person=%s",
        event_id, len(hosts), len(recipients), person_id,
    )
    if not recipients:
        return

    person_row = (
        db.table("person")
        .select("first_name, last_name")
        .eq("person_id", person_id)
        .maybe_single()
        .execute()
    )
    person_data = (person_row.data if person_row else None) or {}
    first = person_data.get("first_name") or ""
    last = person_data.get("last_name") or ""
    full_name = (first + " " + last).strip() or "Jemand"

    title = _event_title(db, event_id) or "Event"
    payload = {"event_title": title, "participant_name": full_name}
    _insert_notifications(db, recipients, "participant_cancelled", event_id, payload)
    _push_to_recipients(
        db,
        recipients,
        title=title,
        body=f"{full_name} hat abgesagt.",
        data={"type": "participant_cancelled", "eventId": event_id},
    )


# ───────────────────────────── Lese-API (User-Scope, RLS) ─────────────────────────────


def list_for_person(person_id: str, token: str, limit: int = 20, before_id: str | None = None) -> list[dict]:
    """Liefert die Benachrichtigungen des Users, neueste zuerst, paginiert nach notification_id."""
    sb = get_supabase_for_user(token)
    query = (
        sb.table("notification")
        .select("notification_id, event_id, type, payload, created_at, read_at")
        .eq("recipient_person_id", person_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if before_id:
        # Cursor: alles älter als das übergebene `before_id`
        before_row = (
            sb.table("notification")
            .select("created_at")
            .eq("notification_id", before_id)
            .maybe_single()
            .execute()
        )
        if before_row and before_row.data:
            query = query.lt("created_at", before_row.data["created_at"])
    return query.execute().data or []


def unread_count(person_id: str, token: str) -> int:
    sb = get_supabase_for_user(token)
    res = (
        sb.table("notification")
        .select("notification_id", count="exact")
        .eq("recipient_person_id", person_id)
        .is_("read_at", "null")
        .execute()
    )
    return res.count or 0


def mark_read(notification_id: str, person_id: str, token: str) -> bool:
    sb = get_supabase_for_user(token)
    from datetime import datetime, timezone
    res = (
        sb.table("notification")
        .update({"read_at": datetime.now(timezone.utc).isoformat()})
        .eq("notification_id", notification_id)
        .eq("recipient_person_id", person_id)
        .is_("read_at", "null")
        .execute()
    )
    return bool(res.data)


def mark_all_read(person_id: str, token: str) -> int:
    sb = get_supabase_for_user(token)
    from datetime import datetime, timezone
    res = (
        sb.table("notification")
        .update({"read_at": datetime.now(timezone.utc).isoformat()})
        .eq("recipient_person_id", person_id)
        .is_("read_at", "null")
        .execute()
    )
    return len(res.data or [])


# ───────────────────────────── Diagnose / Test ─────────────────────────────


def send_test_notification(recipient_person_id: str) -> int:
    """Erzeugt eine Test-Benachrichtigung + Push (Web + Expo) für genau einen Empfänger.

    Liefert die Summe der erfolgreich gesendeten Push-Nachrichten zurück
    (Web-Subs + Expo-Tokens). In-App-Eintrag wird unabhängig davon angelegt.
    """
    db = get_supabase_admin()
    payload = {"event_title": "Test-Benachrichtigung", "changed_fields": ["title"]}
    _insert_notifications(db, [recipient_person_id], "event_updated", None, payload)

    push_title = "Happin Test"
    push_body = "Wenn du das siehst, funktionieren Push & Notifications."
    push_data = {"type": "event_updated"}

    # ── Web Push ──────────────────────────────────────────────────────────
    web_pushed = 0
    try:
        subs = (
            db.table("web_push_subscription")
            .select("endpoint, p256dh_key, auth_key")
            .eq("person_id", recipient_person_id)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[notifications] Test-Subs-Fetch fehlgeschlagen: %s", exc)
        subs = []

    if subs:
        try:
            from app.services.reminder_scheduler import _send_push  # type: ignore
        except Exception as exc:
            logger.info("[notifications] Push-Helper nicht verfügbar: %s", exc)
            _send_push = None  # type: ignore
        if _send_push:
            web_payload = {"title": push_title, "body": push_body, **push_data}
            for sub in subs:
                try:
                    if _send_push(sub["endpoint"], sub["p256dh_key"], sub["auth_key"], web_payload):
                        web_pushed += 1
                except Exception as exc:
                    logger.warning("[notifications] Test-Web-Push fehlgeschlagen: %s", exc)

    # ── Expo Push ─────────────────────────────────────────────────────────
    expo_pushed = 0
    try:
        rows = (
            db.table("expo_push_token")
            .select("token")
            .eq("person_id", recipient_person_id)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[notifications] Test-Expo-Token-Fetch fehlgeschlagen: %s", exc)
        rows = []

    expo_tokens = [r["token"] for r in rows if r.get("token")]
    if expo_tokens:
        try:
            from app.services import expo_push_service
            expo_pushed = expo_push_service.send_to_tokens(
                expo_tokens, push_title, push_body, push_data
            )
        except Exception as exc:
            logger.warning("[notifications] Test-Expo-Push fehlgeschlagen: %s", exc)

    logger.info(
        "[notifications] Test-Push result: web=%d/%d expo=%d/%d",
        web_pushed, len(subs), expo_pushed, len(expo_tokens),
    )
    return web_pushed + expo_pushed
