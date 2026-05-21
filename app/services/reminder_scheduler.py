"""Reminder-Scheduler für Web Push (Anforderung K4).

Läuft als Background-Job im FastAPI-Lifespan. Sucht alle paar Sekunden
nach fälligen Erinnerungen (Event-Start - lead_time_minutes liegt im
nächsten Intervall) und sendet Web-Push-Nachrichten via VAPID an alle
registrierten Subscriptions der jeweiligen Person.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pywebpush import WebPushException, webpush

from app.core.config import settings
from app.core.supabase import get_supabase_admin

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _vapid_claims() -> dict:
    return {"sub": settings.VAPID_SUBJECT}


def _send_push(endpoint: str, p256dh: str, auth: str, payload: dict) -> bool:
    """Sendet eine Push-Nachricht. Gibt True bei Erfolg zurück.

    Bei 404/410 (Subscription erloschen) wird der Endpoint aus der Datenbank
    entfernt.
    """
    try:
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=_vapid_claims(),
        )
        return True
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None) if exc.response else None
        if status in (404, 410):
            logger.info("[reminders] Lösche erloschene Subscription %s", endpoint[:60])
            try:
                get_supabase_admin().table("web_push_subscription").delete().eq(
                    "endpoint", endpoint
                ).execute()
            except Exception as cleanup_err:  # pragma: no cover
                logger.warning("[reminders] Cleanup fehlgeschlagen: %s", cleanup_err)
        else:
            logger.warning("[reminders] WebPushException: %s", exc)
        return False
    except Exception as exc:  # pragma: no cover
        logger.exception("[reminders] Push-Versand fehlgeschlagen: %s", exc)
        return False


def _dispatch_due_reminders() -> None:
    """Holt fällige Reminder und sendet Web Push pro Subscription.

    Ein Reminder ist fällig, wenn der Trigger-Zeitpunkt
    `event.starts_at - lead_time` bereits erreicht/überschritten ist
    UND `event.starts_at` noch in der Zukunft liegt UND der Reminder noch
    nicht in `reminder_sent` steht. So fangen wir auch verpasste Ticks
    auf, ohne ein eng definiertes Zeitfenster zu brauchen.
    """
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return

    db = get_supabase_admin()
    now = datetime.now(timezone.utc)

    try:
        prefs = (
            db.table("reminder_preference")
            .select("person_id, lead_time_minutes")
            .eq("enabled", True)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[reminders] Prefs konnten nicht geladen werden: %s", exc)
        return

    if not prefs:
        return

    for pref in prefs:
        person_id = pref["person_id"]
        lead = pref["lead_time_minutes"]
        # Trigger-Zeit ist starts_at - lead. Fällig: trigger_time <= now.
        # Äquivalent: starts_at <= now + lead.
        latest_starts_at = now + timedelta(minutes=lead)

        try:
            participations = (
                db.table("event_participation")
                .select("event_id")
                .eq("person_id", person_id)
                .eq("status", "Accepted")
                .execute()
                .data
                or []
            )
        except Exception as exc:
            logger.warning("[reminders] Participations Fehler: %s", exc)
            continue

        if not participations:
            continue
        event_ids = [p["event_id"] for p in participations]

        try:
            events = (
                db.table("event")
                .select("event_id, title, starts_at")
                .in_("event_id", event_ids)
                .is_("deleted_at", "null")
                .gt("starts_at", now.isoformat())
                .lte("starts_at", latest_starts_at.isoformat())
                .execute()
                .data
                or []
            )
        except Exception as exc:
            logger.warning("[reminders] Events Fehler: %s", exc)
            continue

        if not events:
            continue

        try:
            already = (
                db.table("reminder_sent")
                .select("event_id")
                .eq("person_id", person_id)
                .in_("event_id", [e["event_id"] for e in events])
                .execute()
                .data
                or []
            )
        except Exception:
            already = []
        sent_ids = {a["event_id"] for a in already}

        try:
            subs = (
                db.table("web_push_subscription")
                .select("endpoint, p256dh_key, auth_key")
                .eq("person_id", person_id)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            logger.warning("[reminders] Subs Fehler: %s", exc)
            continue

        if not subs:
            logger.info(
                "[reminders] Person %s hat fällige Events aber keine Web-Push-Subscription",
                person_id,
            )
            continue

        for event in events:
            if event["event_id"] in sent_ids:
                continue
            payload = {
                "title": event["title"],
                "body": f"Beginnt in {lead} Minuten.",
                "eventId": event["event_id"],
            }
            success = False
            for sub in subs:
                if _send_push(
                    sub["endpoint"], sub["p256dh_key"], sub["auth_key"], payload
                ):
                    success = True

            if success:
                logger.info(
                    "[reminders] Push gesendet für event=%s person=%s",
                    event["event_id"],
                    person_id,
                )
                try:
                    db.table("reminder_sent").insert(
                        {"event_id": event["event_id"], "person_id": person_id}
                    ).execute()
                except Exception as exc:
                    logger.warning("[reminders] reminder_sent Insert: %s", exc)


def start_scheduler() -> None:
    global _scheduler
    if not settings.REMINDER_SCHEDULER_ENABLED:
        logger.info("[reminders] Scheduler deaktiviert (Setting)")
        return
    if not settings.VAPID_PRIVATE_KEY:
        logger.info("[reminders] Scheduler übersprungen — VAPID_PRIVATE_KEY fehlt")
        return
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _dispatch_due_reminders,
        trigger=IntervalTrigger(seconds=settings.REMINDER_SCHEDULER_INTERVAL_SECONDS),
        id="reminder_dispatch",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        "[reminders] Scheduler gestartet (Intervall: %ss)",
        settings.REMINDER_SCHEDULER_INTERVAL_SECONDS,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[reminders] Scheduler gestoppt")
