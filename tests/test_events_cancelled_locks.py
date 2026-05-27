"""Tests for cancel-locks: actions on cancelled events return 400 event_cancelled."""

from datetime import datetime
from unittest.mock import MagicMock, patch

_mock_supabase = MagicMock()

with patch("supabase.create_client", return_value=_mock_supabase):
    from fastapi.testclient import TestClient
    from app.main import app

client = TestClient(app)


def _ensure_active_mock(cancelled: bool, found: bool = True):
    """Build a supabase mock for _ensure_event_active."""
    mock_sb = MagicMock()
    row = MagicMock()
    if not found:
        row.data = None
    else:
        row.data = {
            "event_id": "event-1",
            "cancelled_at": "2026-05-27T10:00:00+00:00" if cancelled else None,
        }
    mock_sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = row
    return mock_sb


def test_ensure_event_active_raises_when_cancelled():
    """_ensure_event_active raises ValueError('event_cancelled') if cancelled_at set."""
    import pytest
    mock_sb = _ensure_active_mock(cancelled=True)
    with patch("app.services.event_service.get_supabase_for_user", return_value=mock_sb):
        from app.services.event_service import _ensure_event_active
        with pytest.raises(ValueError, match="event_cancelled"):
            _ensure_event_active("event-1", "token")


def test_ensure_event_active_raises_when_not_found():
    """_ensure_event_active raises ValueError('event_not_found') if event missing."""
    import pytest
    mock_sb = _ensure_active_mock(cancelled=False, found=False)
    with patch("app.services.event_service.get_supabase_for_user", return_value=mock_sb):
        from app.services.event_service import _ensure_event_active
        with pytest.raises(ValueError, match="event_not_found"):
            _ensure_event_active("event-1", "token")


def test_ensure_event_active_returns_row_when_active():
    """_ensure_event_active returns row dict when event is active."""
    mock_sb = _ensure_active_mock(cancelled=False)
    with patch("app.services.event_service.get_supabase_for_user", return_value=mock_sb):
        from app.services.event_service import _ensure_event_active
        result = _ensure_event_active("event-1", "token")
        assert result["event_id"] == "event-1"
        assert result["cancelled_at"] is None


def test_rsvp_on_cancelled_event_returns_400():
    """POST /api/v1/events/{id}/rsvp returns 400 when event is cancelled."""
    with patch("app.services.event_service.rsvp_event") as mock_rsvp, \
         patch("app.core.auth.get_current_user") as mock_user:
        mock_user.return_value = MagicMock(user=MagicMock(id="uid-1", email="a@b.de"))
        mock_rsvp.side_effect = ValueError("event_cancelled")

        resp = client.post(
            "/api/v1/events/event-1/rsvp",
            json={"status": "Accepted"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 400
        assert "abgesagt" in resp.json()["detail"].lower()


def test_patch_event_on_cancelled_event_returns_400():
    """PATCH /api/v1/events/{id} returns 400 when event is cancelled."""
    with patch("app.services.event_service.update_event") as mock_update, \
         patch("app.services.person_service.get_or_create_person") as mock_person, \
         patch("app.core.auth.get_current_user") as mock_user:
        mock_user.return_value = MagicMock(user=MagicMock(id="uid-1", email="a@b.de"))
        mock_person.return_value = {"person_id": "p-1"}
        mock_update.side_effect = ValueError("event_cancelled")

        resp = client.patch(
            "/api/v1/events/event-1",
            json={"title": "New title"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 400
        assert "abgesagt" in resp.json()["detail"].lower()


def test_checkout_on_cancelled_event_returns_400():
    """POST /api/v1/payments/checkout returns 400 when event is cancelled."""
    with patch("app.services.payment_service.create_checkout_session") as mock_co, \
         patch("app.services.person_service.get_or_create_person") as mock_person, \
         patch("app.core.auth.get_current_user") as mock_user:
        mock_user.return_value = MagicMock(user=MagicMock(id="uid-1", email="a@b.de"))
        mock_person.return_value = {"person_id": "p-1"}
        mock_co.side_effect = ValueError("event_cancelled")

        resp = client.post(
            "/api/v1/events/event-1/checkout-session",
            json={"ticket_option_id": "opt-1", "quantity": 1},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 400
        assert "abgesagt" in resp.json()["detail"].lower()


def test_custom_field_responses_on_cancelled_event_returns_400():
    """POST /api/v1/events/{id}/custom-fields/responses returns 400 when event cancelled."""
    mock_sb = _ensure_active_mock(cancelled=True)
    with patch("app.core.supabase.get_supabase_for_user", return_value=mock_sb), \
         patch("app.services.event_service.get_supabase_for_user", return_value=mock_sb), \
         patch("app.services.person_service.get_or_create_person") as mock_person, \
         patch("app.core.auth.get_current_user") as mock_user:
        mock_user.return_value = MagicMock(user=MagicMock(id="uid-1", email="a@b.de"))
        mock_person.return_value = {"person_id": "p-1"}

        resp = client.post(
            "/api/v1/events/event-1/custom-fields/responses",
            json={"ticket_id": "tic-1", "responses": []},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 400
        assert "abgesagt" in resp.json()["detail"].lower()
