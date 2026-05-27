"""Email delivery via Resend."""

from __future__ import annotations

import html
import logging
from datetime import datetime

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> None:
    resend.api_key = settings.RESEND_API_KEY


def send_waitlist_promotion_email(
    *,
    email: str,
    name: str,
    event_title: str,
    event_link: str,
    expires_at: datetime,
) -> None:
    """Notify a paid-event waitlist member that a spot is available."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping waitlist promotion email")
        return
    _get_client()
    deadline = expires_at.strftime("%d.%m.%Y %H:%M Uhr")
    safe_name = html.escape(name)
    safe_title = html.escape(event_title)
    safe_link = html.escape(str(event_link or ""))
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [email],
        "subject": f"Dein Platz bei '{event_title}' ist frei!",
        "html": (
            f"<p>Hallo {safe_name},</p>"
            f"<p>Ein Platz bei <strong>{safe_title}</strong> ist für dich frei geworden!</p>"
            f"<p>Du hast Zeit bis <strong>{deadline}</strong>, um deinen Platz zu buchen. "
            f"Danach wird der Platz an die nächste Person auf der Warteliste weitergegeben.</p>"
            f'<p><a href="{event_link}">{safe_link}</a></p>'
            f"<p>Viele Grüße,<br>Das Happin-Team</p>"
        ),
    }
    try:
        resend.Emails.send(params)
    except Exception:
        logger.exception("Failed to send waitlist promotion email to %s", email)


def send_waitlist_confirmation_email(
    *,
    email: str,
    name: str,
    event_title: str,
) -> None:
    """Notify a free-event waitlist member that they have been auto-registered."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping waitlist confirmation email")
        return
    _get_client()
    safe_name = html.escape(name)
    safe_title = html.escape(event_title)
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [email],
        "subject": f"Du bist jetzt dabei: '{event_title}'",
        "html": (
            f"<p>Hallo {safe_name},</p>"
            f"<p>Gute Nachrichten! Ein Platz bei <strong>{safe_title}</strong> "
            f"ist frei geworden und du wurdest automatisch als Teilnehmer eingetragen.</p>"
            f"<p>Dein Ticket ist jetzt in der Happin-App verfügbar.</p>"
            f"<p>Viele Grüße,<br>Das Happin-Team</p>"
        ),
    }
    try:
        resend.Emails.send(params)
    except Exception:
        logger.exception("Failed to send waitlist confirmation email to %s", email)
