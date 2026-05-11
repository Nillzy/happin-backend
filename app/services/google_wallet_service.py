"""Google Wallet service for generating event ticket passes."""

import json
import time
import uuid
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials

from app.core.config import settings
from app.core.supabase import get_supabase, get_supabase_for_user


# Google Wallet API scopes
SCOPES = ["https://www.googleapis.com/auth/wallet_object.issuer"]

# Base URL for "Add to Google Wallet" links
WALLET_BASE_URL = "https://pay.google.com/gp/v/save"


def _get_credentials() -> Credentials | None:
    """Load Google Service Account credentials."""
    if not settings.GOOGLE_SERVICE_ACCOUNT_FILE:
        return None

    try:
        credentials = Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=SCOPES,
        )
        return credentials
    except Exception:
        return None


def _format_location(location: dict | None) -> str | None:
    """Format location dict into a single address string."""
    if not location:
        return None

    parts = []
    if location.get("street"):
        street = location["street"]
        if location.get("house_number"):
            street += f" {location['house_number']}"
        parts.append(street)

    if location.get("postal_code") or location.get("city"):
        city_part = " ".join(
            filter(None, [location.get("postal_code"), location.get("city")])
        )
        if city_part:
            parts.append(city_part)

    if location.get("country"):
        parts.append(location["country"])

    return ", ".join(parts) if parts else None


def get_event_for_wallet(event_id: str, token: str | None = None) -> dict | None:
    """Fetch event data needed for wallet pass generation."""
    supabase = get_supabase_for_user(token) if token else get_supabase()

    response = (
        supabase.table("event")
        .select(
            "event_id, title, description, starts_at, ends_at, "
            "location(*), event_media(media_url)"
        )
        .eq("event_id", event_id)
        .maybe_single()
        .execute()
    )

    if not response or not response.data:
        return None

    return response.data


def _parse_event_times(event_data: dict) -> tuple[datetime, datetime]:
    """Parse start and end datetime from event data."""
    starts_at = datetime.fromisoformat(
        event_data["starts_at"].replace("Z", "+00:00")
    )
    if event_data.get("ends_at"):
        ends_at = datetime.fromisoformat(
            event_data["ends_at"].replace("Z", "+00:00")
        )
    else:
        ends_at = starts_at + timedelta(hours=2)
    return starts_at, ends_at


def _create_event_ticket_class(issuer_id: str, class_id: str, event_data: dict) -> dict:
    """Create a Google Wallet EventTicketClass payload for inline JWT embedding.

    Class-level fields (eventName, venue, dateTime, classTemplateInfo) must live
    here — Google ignores them if placed on the object.
    """
    starts_at, ends_at = _parse_event_times(event_data)

    location = event_data.get("location")
    venue_name = location.get("city", "Venue") if location else "Venue"
    venue_address = _format_location(location)

    media = event_data.get("event_media") or []
    hero_image_url = media[0]["media_url"] if media else None

    ticket_class: dict = {
        "id": class_id,
        "issuerName": "Happin",
        "reviewStatus": "UNDER_REVIEW",
        "eventName": {
            "defaultValue": {
                "language": "de",
                "value": event_data["title"],
            }
        },
        "venue": {
            "name": {
                "defaultValue": {
                    "language": "de",
                    "value": venue_name,
                }
            },
        },
        "dateTime": {
            "start": starts_at.isoformat(),
            "end": ends_at.isoformat(),
        },
        "classTemplateInfo": {
            "cardRowTemplateInfos": [
                {
                    "twoItems": {
                        "startItem": {
                            "firstValue": {
                                "fields": [
                                    {"fieldPath": "object.textModulesData['date']"}
                                ]
                            }
                        },
                        "endItem": {
                            "firstValue": {
                                "fields": [
                                    {"fieldPath": "object.textModulesData['time']"}
                                ]
                            }
                        },
                    }
                }
            ]
        },
    }

    if venue_address:
        ticket_class["venue"]["address"] = {
            "defaultValue": {
                "language": "de",
                "value": venue_address,
            }
        }

    if hero_image_url:
        ticket_class["heroImage"] = {
            "sourceUri": {"uri": hero_image_url}
        }

    return ticket_class


def _create_event_ticket_object(
    event_data: dict,
    object_id: str,
    class_id: str,
    qr_token: str,
    guest_name: str | None = None,
) -> dict:
    """Create a Google Wallet EventTicketObject payload.

    Only object-level fields belong here. Class-level fields (eventName, venue,
    dateTime, classTemplateInfo) must be on the class, not here.
    """
    issuer_id = settings.GOOGLE_WALLET_ISSUER_ID
    starts_at, ends_at = _parse_event_times(event_data)

    return {
        "id": f"{issuer_id}.{object_id}",
        "classId": class_id,
        "state": "ACTIVE",
        "barcode": {
            "type": "QR_CODE",
            "value": qr_token,
            "alternateText": object_id[:8].upper(),
        },
        "ticketHolderName": guest_name or "Happin User",
        "ticketNumber": object_id[:8].upper(),
        "textModulesData": [
            {
                "id": "date",
                "header": "DATUM",
                "body": starts_at.strftime("%d.%m.%Y"),
            },
            {
                "id": "time",
                "header": "UHRZEIT",
                "body": f"{starts_at.strftime('%H:%M')} - {ends_at.strftime('%H:%M')}",
            },
        ],
        "linksModuleData": {
            "uris": [
                {
                    "uri": f"https://happin.app/events/{event_data['event_id']}",
                    "description": "Event in Happin öffnen",
                    "id": "happin_link",
                }
            ]
        },
    }


def generate_wallet_link(
    event_id: str,
    token: str | None = None,
    qr_token: str | None = None,
    guest_name: str | None = None,
) -> str | None:
    """
    Generate a Google Wallet "Add to Wallet" link for an event.

    Args:
        event_id: The UUID of the event
        token: Optional JWT token for accessing private events

    Returns:
        The "Add to Google Wallet" URL, or None if generation fails
    """
    if not settings.GOOGLE_WALLET_ISSUER_ID or not settings.GOOGLE_SERVICE_ACCOUNT_FILE:
        return None

    # Load private key directly from the service account JSON — the Credentials
    # object does not expose the raw key bytes needed for PyJWT signing.
    try:
        with open(settings.GOOGLE_SERVICE_ACCOUNT_FILE) as f:
            sa_info = json.load(f)
        private_key = sa_info["private_key"]
        service_account_email = sa_info["client_email"]
    except Exception:
        return None

    event_data = get_event_for_wallet(event_id, token)
    if not event_data:
        return None

    issuer_id = settings.GOOGLE_WALLET_ISSUER_ID
    # Per-event class ID so different events don't share/overwrite the same class.
    class_id = f"{issuer_id}.event-{event_id}"
    object_id = str(uuid.uuid4())

    ticket_class = _create_event_ticket_class(issuer_id, class_id, event_data)
    ticket_object = _create_event_ticket_object(
        event_data, object_id, class_id,
        qr_token=qr_token or f"happin:{event_id}:{object_id}",
        guest_name=guest_name,
    )

    # origins must be empty for native app calls (non-web origin)
    claims = {
        "iss": service_account_email,
        "aud": "google",
        "origins": [],
        "typ": "savetowallet",
        "iat": int(time.time()),
        "payload": {
            "eventTicketClasses": [ticket_class],
            "eventTicketObjects": [ticket_object],
        },
    }

    import jwt

    token_jwt = jwt.encode(claims, private_key, algorithm="RS256")

    return f"{WALLET_BASE_URL}/{token_jwt}"


def is_configured() -> bool:
    """Check if Google Wallet integration is properly configured."""
    return bool(
        settings.GOOGLE_WALLET_ISSUER_ID
        and settings.GOOGLE_SERVICE_ACCOUNT_FILE
        and _get_credentials()
    )
