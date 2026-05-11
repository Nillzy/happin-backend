"""Tests for Google Wallet integration."""

import json
from unittest.mock import MagicMock, mock_open, patch


MOCK_EVENT_FOR_WALLET = {
    "event_id": "35b43254-4e21-459f-b729-4cb3966cf322",
    "title": "Techno Night Berlin",
    "description": "Eine legendäre Nacht.",
    "starts_at": "2026-05-10T22:00:00+00:00",
    "ends_at": "2026-05-11T06:00:00+00:00",
    "location": {
        "location_id": "8fa1205a-aca8-4243-8169-b5af4fd27833",
        "street": "Revaler Str.",
        "house_number": "99",
        "postal_code": "10245",
        "city": "Berlin",
        "country": "Deutschland",
    },
    "event_media": [
        {"media_url": "https://example.com/event-image.jpg"},
    ],
}

MOCK_TICKET = {
    "ticket_id": "ticket-uuid-123",
    "qr_token": "eyJ0ZXN0fQ.abc12345",
    "guest_name": "Test User",
    "status": "active",
}


def _mock_wallet_chain(mock_supabase, data):
    """Set up mock for wallet service queries."""
    table_mock = mock_supabase.table.return_value
    select_mock = table_mock.select.return_value
    eq_mock = select_mock.eq.return_value
    maybe_single_mock = eq_mock.maybe_single.return_value

    response = MagicMock()
    response.data = data
    maybe_single_mock.execute.return_value = response


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_auth():
    return MagicMock(user=MagicMock(id="uid-123", email="test@example.com"))


def test_wallet_endpoint_not_configured(client, mock_supabase):
    """Test that 503 is returned when Google Wallet is not configured."""
    with patch("app.core.auth.get_current_user", return_value=_mock_auth()), \
         patch("app.api.v1.events.person_service.get_or_create_person", return_value={"person_id": "pid-1"}), \
         patch("app.api.v1.events.ticket_service.get_tickets_for_event", return_value=[MOCK_TICKET]), \
         patch("app.services.google_wallet_service.is_configured", return_value=False):
        response = client.get(
            "/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/wallet",
            headers=_auth_headers(),
        )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_wallet_endpoint_event_not_found(client, mock_supabase):
    """Test that 404 is returned for non-existent events."""
    _mock_wallet_chain(mock_supabase, None)

    with patch("app.core.auth.get_current_user", return_value=_mock_auth()), \
         patch("app.api.v1.events.person_service.get_or_create_person", return_value={"person_id": "pid-1"}), \
         patch("app.api.v1.events.ticket_service.get_tickets_for_event", return_value=[MOCK_TICKET]), \
         patch("app.services.google_wallet_service.is_configured", return_value=True), \
         patch("app.services.google_wallet_service._get_credentials") as mock_creds:
        mock_creds.return_value = MagicMock(
            service_account_email="test@test.iam.gserviceaccount.com"
        )
        response = client.get(
            "/api/v1/events/00000000-0000-0000-0000-000000000000/wallet",
            headers=_auth_headers(),
        )

    assert response.status_code == 404


def test_wallet_endpoint_no_ticket(client, mock_supabase):
    """Test that 404 is returned when user has no ticket for the event."""
    with patch("app.core.auth.get_current_user", return_value=_mock_auth()), \
         patch("app.api.v1.events.person_service.get_or_create_person", return_value={"person_id": "pid-1"}), \
         patch("app.api.v1.events.ticket_service.get_tickets_for_event", return_value=[]), \
         patch("app.services.google_wallet_service.is_configured", return_value=True):
        response = client.get(
            "/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/wallet",
            headers=_auth_headers(),
        )

    assert response.status_code == 404
    assert "Ticket" in response.json()["detail"]


def test_wallet_endpoint_returns_url(client, mock_supabase):
    """Test that the wallet endpoint returns a wallet URL."""
    _mock_wallet_chain(mock_supabase, MOCK_EVENT_FOR_WALLET)

    mock_credentials = MagicMock()
    mock_credentials.service_account_email = "test@test.iam.gserviceaccount.com"

    fake_sa = json.dumps({
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
        "client_email": "test@test.iam.gserviceaccount.com",
    })

    with patch("app.core.auth.get_current_user", return_value=_mock_auth()), \
         patch("app.api.v1.events.person_service.get_or_create_person", return_value={"person_id": "pid-1"}), \
         patch("app.api.v1.events.ticket_service.get_tickets_for_event", return_value=[MOCK_TICKET]), \
         patch("app.services.google_wallet_service.is_configured", return_value=True), \
         patch("app.services.google_wallet_service._get_credentials", return_value=mock_credentials), \
         patch("app.services.google_wallet_service.settings") as mock_settings, \
         patch("builtins.open", mock_open(read_data=fake_sa)), \
         patch("jwt.encode", return_value="test-jwt-token"):
        mock_settings.GOOGLE_WALLET_ISSUER_ID = "3388000000023116326"
        mock_settings.GOOGLE_SERVICE_ACCOUNT_FILE = "/path/to/file.json"

        response = client.get(
            "/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/wallet",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert "wallet_url" in body
    assert body["wallet_url"].startswith("https://pay.google.com/gp/v/save/")


def test_wallet_endpoint_barcode_uses_qr_token(client, mock_supabase):
    """Test that the wallet pass barcode uses the ticket's qr_token."""
    _mock_wallet_chain(mock_supabase, MOCK_EVENT_FOR_WALLET)

    fake_sa = json.dumps({
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
        "client_email": "test@test.iam.gserviceaccount.com",
    })

    captured = {}

    def fake_jwt_encode(claims, *args, **kwargs):
        captured["claims"] = claims
        return "test-jwt-token"

    with patch("app.core.auth.get_current_user", return_value=_mock_auth()), \
         patch("app.api.v1.events.person_service.get_or_create_person", return_value={"person_id": "pid-1"}), \
         patch("app.api.v1.events.ticket_service.get_tickets_for_event", return_value=[MOCK_TICKET]), \
         patch("app.services.google_wallet_service.is_configured", return_value=True), \
         patch("app.services.google_wallet_service._get_credentials", return_value=MagicMock()), \
         patch("app.services.google_wallet_service.settings") as mock_settings, \
         patch("builtins.open", mock_open(read_data=fake_sa)), \
         patch("jwt.encode", side_effect=fake_jwt_encode):
        mock_settings.GOOGLE_WALLET_ISSUER_ID = "3388000000023116326"
        mock_settings.GOOGLE_SERVICE_ACCOUNT_FILE = "/path/to/file.json"

        client.get(
            "/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/wallet",
            headers=_auth_headers(),
        )

    objects = captured["claims"]["payload"]["eventTicketObjects"]
    assert objects[0]["barcode"]["value"] == MOCK_TICKET["qr_token"]
    assert objects[0]["ticketHolderName"] == MOCK_TICKET["guest_name"]


def test_format_location():
    """Test location formatting helper function."""
    from app.services.google_wallet_service import _format_location

    location = {
        "street": "Revaler Str.",
        "house_number": "99",
        "postal_code": "10245",
        "city": "Berlin",
        "country": "Deutschland",
    }
    result = _format_location(location)
    assert result == "Revaler Str. 99, 10245 Berlin, Deutschland"

    partial = {"city": "Berlin", "country": "Deutschland"}
    result = _format_location(partial)
    assert result == "Berlin, Deutschland"

    assert _format_location(None) is None
    assert _format_location({}) is None


def test_create_event_ticket_object():
    """Test that EventTicketObject is created with correct structure."""
    from app.services.google_wallet_service import _create_event_ticket_object

    class_id = "3388000000023116326.event-35b43254-4e21-459f-b729-4cb3966cf322"
    qr_token = "eyJ0ZXN0fQ.abc12345"

    with patch("app.services.google_wallet_service.settings") as mock_settings:
        mock_settings.GOOGLE_WALLET_ISSUER_ID = "3388000000023116326"

        ticket = _create_event_ticket_object(
            MOCK_EVENT_FOR_WALLET,
            "test-object-id",
            class_id,
            qr_token=qr_token,
            guest_name="Test User",
        )

    assert ticket["id"] == "3388000000023116326.test-object-id"
    assert ticket["classId"] == class_id
    assert ticket["state"] == "ACTIVE"
    assert ticket["barcode"]["type"] == "QR_CODE"
    assert ticket["barcode"]["value"] == qr_token
    assert ticket["ticketHolderName"] == "Test User"
    assert "eventName" not in ticket
    assert "venue" not in ticket
    assert "dateTime" not in ticket
    assert "classTemplateInfo" not in ticket


def test_wallet_event_without_end_time():
    """Test that events without end_at get a default 2-hour duration."""
    from app.services.google_wallet_service import _create_event_ticket_object

    event_no_end = {**MOCK_EVENT_FOR_WALLET, "ends_at": None}
    class_id = "3388000000023116326.event-test"

    with patch("app.services.google_wallet_service.settings") as mock_settings:
        mock_settings.GOOGLE_WALLET_ISSUER_ID = "3388000000023116326"

        ticket = _create_event_ticket_object(
            event_no_end, "test-object-id", class_id, qr_token="test-token",
        )

    assert ticket["barcode"]["type"] == "QR_CODE"


def test_wallet_event_without_location():
    """Test that events without location still generate valid ticket."""
    from app.services.google_wallet_service import _create_event_ticket_object

    event_no_location = {**MOCK_EVENT_FOR_WALLET, "location": None}
    class_id = "3388000000023116326.event-test"

    with patch("app.services.google_wallet_service.settings") as mock_settings:
        mock_settings.GOOGLE_WALLET_ISSUER_ID = "3388000000023116326"

        ticket = _create_event_ticket_object(
            event_no_location, "test-object-id", class_id, qr_token="test-token",
        )

    assert ticket["classId"] == class_id


def test_wallet_event_without_image():
    """Test that events without image don't include heroImage."""
    from app.services.google_wallet_service import _create_event_ticket_object

    event_no_image = {**MOCK_EVENT_FOR_WALLET, "event_media": []}
    class_id = "3388000000023116326.event-test"

    with patch("app.services.google_wallet_service.settings") as mock_settings:
        mock_settings.GOOGLE_WALLET_ISSUER_ID = "3388000000023116326"

        ticket = _create_event_ticket_object(
            event_no_image, "test-object-id", class_id, qr_token="test-token",
        )

    assert "heroImage" not in ticket
