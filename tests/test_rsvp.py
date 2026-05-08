"""Tests for RSVP endpoint and rsvp_event service function."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


EVENT_ID = "35b43254-4e21-459f-b729-4cb3966cf322"
PERSON_ID = "c1d2e3f4-a5b6-7890-cdef-123456789012"
PARTICIPATION_ID = "d4e5f6a7-b8c9-0123-defa-234567890123"

PARTICIPATION_DATA = {
    "event_participation_id": PARTICIPATION_ID,
    "event_id": EVENT_ID,
    "person_id": PERSON_ID,
    "status": "Accepted",
}


@pytest.fixture
def mock_supabase_for_user():
    with patch("app.services.event_service.get_supabase_for_user") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_person():
    with patch("app.services.person_service.get_or_create_person") as mock:
        mock.return_value = {"person_id": PERSON_ID}
        yield mock


def _setup_event_and_participation(mock_client, starts_at, is_public, participation_status="Accepted"):
    """Helper: configure mock for event fetch + RPC success + participation fetch."""
    event_table = MagicMock()
    event_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "starts_at": starts_at,
        "is_public": is_public,
    }

    participation_table = MagicMock()
    participation_table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        **PARTICIPATION_DATA,
        "status": participation_status,
    }

    def table_side_effect(name):
        if name == "event":
            return event_table
        return participation_table

    mock_client.table.side_effect = table_side_effect
    mock_client.rpc.return_value.execute.return_value.data = {"success": True}


class TestRsvpEventService:
    """Unit tests for the rsvp_event service function."""

    def test_successful_rsvp_returns_participation(self, mock_supabase_for_user, mock_person):
        from app.services.event_service import rsvp_event

        _setup_event_and_participation(mock_supabase_for_user, "2027-01-01T10:00:00+00:00", True)

        result = rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Accepted", "fake-token")

        assert result["status"] == "Accepted"
        assert result["event_id"] == EVENT_ID
        assert result["event_participation_id"] == PARTICIPATION_ID

    def test_private_event_allows_pending(self, mock_supabase_for_user, mock_person):
        from app.services.event_service import rsvp_event

        _setup_event_and_participation(mock_supabase_for_user, "2027-01-01T10:00:00+00:00", False, "Pending")

        result = rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Pending", "fake-token")

        assert result["status"] == "Pending"

    def test_private_event_allows_declined(self, mock_supabase_for_user, mock_person):
        from app.services.event_service import rsvp_event

        _setup_event_and_participation(mock_supabase_for_user, "2027-01-01T10:00:00+00:00", False, "Declined")

        result = rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Declined", "fake-token")

        assert result["status"] == "Declined"

    def test_raises_event_not_found(self, mock_supabase_for_user, mock_person):
        from app.services.event_service import rsvp_event

        mock_supabase_for_user.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None

        with pytest.raises(ValueError, match="event_not_found"):
            rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Accepted", "fake-token")

    def test_raises_event_in_past(self, mock_supabase_for_user, mock_person):
        from app.services.event_service import rsvp_event

        mock_supabase_for_user.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "starts_at": "2020-01-01T10:00:00+00:00",
            "is_public": True,
        }

        with pytest.raises(ValueError, match="event_in_past"):
            rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Accepted", "fake-token")

    def test_raises_public_event_accepted_only_for_pending(self, mock_supabase_for_user, mock_person):
        from app.services.event_service import rsvp_event

        mock_supabase_for_user.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "starts_at": "2027-01-01T10:00:00+00:00",
            "is_public": True,
        }

        with pytest.raises(ValueError, match="public_event_accepted_only"):
            rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Pending", "fake-token")

    def test_public_event_allows_declined(self, mock_supabase_for_user, mock_person):
        # "Declined" is allowed on public events — only "Pending" is blocked
        from app.services.event_service import rsvp_event

        _setup_event_and_participation(mock_supabase_for_user, "2027-01-01T10:00:00+00:00", True, "Declined")

        result = rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Declined", "fake-token")

        assert result["status"] == "Declined"

    def test_upsert_rsvp_returns_updated_participation(self, mock_supabase_for_user, mock_person):
        # RSVPing a second time (status change) should return the updated participation
        from app.services.event_service import rsvp_event

        _setup_event_and_participation(mock_supabase_for_user, "2027-01-01T10:00:00+00:00", True, "Accepted")

        first = rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Accepted", "fake-token")
        assert first["status"] == "Accepted"

        _setup_event_and_participation(mock_supabase_for_user, "2027-01-01T10:00:00+00:00", False, "Declined")

        second = rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Declined", "fake-token")
        assert second["status"] == "Declined"

    def test_raises_host_cannot_rsvp_from_rpc(self, mock_supabase_for_user, mock_person):
        from app.services.event_service import rsvp_event

        mock_supabase_for_user.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "starts_at": "2027-01-01T10:00:00+00:00",
            "is_public": True,
        }
        mock_supabase_for_user.rpc.return_value.execute.return_value.data = {"error": "host_cannot_rsvp"}

        with pytest.raises(ValueError, match="host_cannot_rsvp"):
            rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Accepted", "fake-token")

    def test_raises_event_full_from_rpc(self, mock_supabase_for_user, mock_person):
        from app.services.event_service import rsvp_event

        mock_supabase_for_user.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "starts_at": "2027-01-01T10:00:00+00:00",
            "is_public": True,
        }
        mock_supabase_for_user.rpc.return_value.execute.return_value.data = {"error": "event_full"}

        with pytest.raises(ValueError, match="event_full"):
            rsvp_event(EVENT_ID, "uid-123", "test@example.com", "Accepted", "fake-token")


class TestRsvpEndpoint:
    """Integration tests for POST /api/v1/events/{event_id}/rsvp."""

    def _make_request(self, status="Accepted", token="fake-token"):
        from app.main import app
        client = TestClient(app)
        kwargs = {"json": {"status": status}}
        if token:
            kwargs["headers"] = {"Authorization": f"Bearer {token}"}
        return client.post(f"/api/v1/events/{EVENT_ID}/rsvp", **kwargs)

    def test_returns_200_on_successful_rsvp(self):
        with patch("app.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = MagicMock(user=MagicMock(id="uid-123", email="test@example.com"))
            with patch("app.services.event_service.rsvp_event", return_value=PARTICIPATION_DATA):
                with patch("app.api.v1.events.person_service.get_or_create_person", return_value={"person_id": "pid-1", "first_name": "Test", "last_name": "User"}):
                    with patch("app.api.v1.events.ticket_service.create_tickets"):
                        mock_sb = MagicMock()
                        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"max_tickets_per_person": 1}
                        with patch("app.core.supabase.get_supabase_for_user", return_value=mock_sb):
                            response = self._make_request()

                            assert response.status_code == 200
                            data = response.json()
                            assert data["status"] == "Accepted"
                            assert data["event_id"] == EVENT_ID
                            assert data["event_participation_id"] == PARTICIPATION_ID

    def test_returns_403_without_token(self):
        response = self._make_request(token=None)

        assert response.status_code == 403

    def test_returns_422_for_invalid_status(self):
        with patch("app.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = MagicMock(user=MagicMock(id="uid-123", email="test@example.com"))
            response = self._make_request(status="InvalidStatus")

            assert response.status_code == 422

    def test_returns_404_when_event_not_found(self):
        with patch("app.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = MagicMock(user=MagicMock(id="uid-123", email="test@example.com"))
            with patch("app.services.event_service.rsvp_event", side_effect=ValueError("event_not_found")):
                response = self._make_request()

                assert response.status_code == 404

    def test_returns_400_when_event_in_past(self):
        with patch("app.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = MagicMock(user=MagicMock(id="uid-123", email="test@example.com"))
            with patch("app.services.event_service.rsvp_event", side_effect=ValueError("event_in_past")):
                response = self._make_request()

                assert response.status_code == 400

    def test_returns_400_when_public_event_pending(self):
        with patch("app.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = MagicMock(user=MagicMock(id="uid-123", email="test@example.com"))
            with patch("app.services.event_service.rsvp_event", side_effect=ValueError("public_event_accepted_only")):
                response = self._make_request(status="Pending")

                assert response.status_code == 400

    def test_returns_400_when_host_tries_to_rsvp(self):
        with patch("app.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = MagicMock(user=MagicMock(id="uid-123", email="test@example.com"))
            with patch("app.services.event_service.rsvp_event", side_effect=ValueError("host_cannot_rsvp")):
                response = self._make_request()

                assert response.status_code == 400

    def test_returns_409_when_event_full(self):
        with patch("app.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = MagicMock(user=MagicMock(id="uid-123", email="test@example.com"))
            with patch("app.services.event_service.rsvp_event", side_effect=ValueError("event_full")):
                response = self._make_request()

                assert response.status_code == 409
