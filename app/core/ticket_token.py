"""HMAC-based ticket token generation and verification."""

import base64
import hashlib
import hmac
import json

from app.core.config import settings


def _get_key() -> bytes:
    return settings.TICKET_SIGNING_KEY.encode()


def generate_ticket_token(
    event_id: str,
    guest_name: str,
    ticket_nr: int,
    option_name: str | None = None,
) -> str:
    """Generate a signed ticket token encoding event, guest, and ticket info."""
    payload = {"eid": event_id, "name": guest_name, "nr": ticket_nr, "opt": option_name}
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload, ensure_ascii=False).encode())
        .decode()
        .rstrip("=")
    )
    sig = hmac.new(_get_key(), payload_b64.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload_b64}.{sig}"


def verify_ticket_token(token: str, event_id: str) -> dict | None:
    """Verify HMAC signature and return payload dict, or None if invalid."""
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return None

    payload_b64, sig = parts
    expected = hmac.new(_get_key(), payload_b64.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig, expected):
        return None

    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding

    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    except (json.JSONDecodeError, ValueError):
        return None

    if payload.get("eid") != event_id:
        return None

    return payload
