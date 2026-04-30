"""Tests for participant management endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    with patch("app.services.event_service.get_supabase") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_person_service():
    """Mock person service to return a person_id."""
    with patch("app.services.person_service.get_or_create_person") as mock:
        mock.return_value = {"person_id": "c1d2e3f4-a5b6-7890-cdef-123456789012"}
        yield mock


class TestIsUserHost:
    """Tests for is_user_host function."""

    def test_returns_true_when_user_is_host(self, mock_supabase):
        """User with Host role returns True."""
        from app.services.event_service import is_user_host

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"event_participation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "role": "Host"}
        )

        result = is_user_host(event_id="35b43254-4e21-459f-b729-4cb3966cf322", person_id="c1d2e3f4-a5b6-7890-cdef-123456789012")

        assert result is True

    def test_returns_false_when_user_is_participant(self, mock_supabase):
        """User with Participant role returns False."""
        from app.services.event_service import is_user_host

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = is_user_host(event_id="35b43254-4e21-459f-b729-4cb3966cf322", person_id="c1d2e3f4-a5b6-7890-cdef-123456789012")

        assert result is False

    def test_returns_false_when_no_participation(self, mock_supabase):
        """User with no participation returns False."""
        from app.services.event_service import is_user_host

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = is_user_host(event_id="35b43254-4e21-459f-b729-4cb3966cf322", person_id="d2e3f4a5-b6c7-8901-def0-234567890123")

        assert result is False


class TestGetEventParticipants:
    """Tests for get_event_participants function."""

    def test_returns_participants_with_counts(self, mock_supabase):
        """Returns participant list with status counts."""
        from app.services.event_service import get_event_participants

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "event_participation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "status": "Accepted",
                    "created_at": "2026-04-20T14:30:00Z",
                    "person": {
                        "person_id": "c1d2e3f4-a5b6-7890-cdef-123456789012",
                        "first_name": "Max",
                        "last_name": "Lehmann",
                        "phone_number": "+49 170 1234567",
                    },
                },
                {
                    "event_participation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "status": "Declined",
                    "created_at": "2026-04-20T15:00:00Z",
                    "person": {
                        "person_id": "d2e3f4a5-b6c7-8901-def0-234567890123",
                        "first_name": "Sophie",
                        "last_name": "Klein",
                        "phone_number": "+49 151 9876543",
                    },
                },
                {
                    "event_participation_id": "c3d4e5f6-a7b8-9012-cdef-234567890123",
                    "status": "Pending",
                    "created_at": "2026-04-20T16:00:00Z",
                    "person": {
                        "person_id": "e3f4a5b6-c7d8-9012-ef01-345678901234",
                        "first_name": "Jonas",
                        "last_name": None,
                        "phone_number": None,
                    },
                },
            ]
        )

        result = get_event_participants(event_id="35b43254-4e21-459f-b729-4cb3966cf322")

        assert len(result["participants"]) == 3
        assert result["counts"]["accepted"] == 1
        assert result["counts"]["declined"] == 1
        assert result["counts"]["pending"] == 1

    def test_returns_empty_list_when_no_participants(self, mock_supabase):
        """Returns empty list with zero counts when no participants."""
        from app.services.event_service import get_event_participants

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = get_event_participants(event_id="35b43254-4e21-459f-b729-4cb3966cf322")

        assert result["participants"] == []
        assert result["counts"]["accepted"] == 0
        assert result["counts"]["declined"] == 0
        assert result["counts"]["pending"] == 0


class TestRemoveParticipants:
    """Tests for remove_participants function."""

    def test_removes_participants_and_returns_count(self, mock_supabase):
        """Removes specified participants and returns count."""
        from app.services.event_service import remove_participants

        mock_supabase.table.return_value.delete.return_value.eq.return_value.in_.return_value.neq.return_value.execute.return_value = MagicMock(
            data=[
                {"event_participation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"},
                {"event_participation_id": "c3d4e5f6-a7b8-9012-cdef-234567890123"},
            ]
        )

        result = remove_participants(event_id="35b43254-4e21-459f-b729-4cb3966cf322", participation_ids=["b2c3d4e5-f6a7-8901-bcde-f12345678901", "c3d4e5f6-a7b8-9012-cdef-234567890123"])

        assert result == 2

    def test_returns_zero_when_no_matches(self, mock_supabase):
        """Returns 0 when no participants match."""
        from app.services.event_service import remove_participants

        mock_supabase.table.return_value.delete.return_value.eq.return_value.in_.return_value.neq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = remove_participants(event_id="35b43254-4e21-459f-b729-4cb3966cf322", participation_ids=["00000000-0000-0000-0000-000000000099"])

        assert result == 0

    def test_does_not_remove_hosts(self, mock_supabase):
        """Does not remove participants with Host role."""
        from app.services.event_service import remove_participants

        # Only non-host participant is removed
        mock_supabase.table.return_value.delete.return_value.eq.return_value.in_.return_value.neq.return_value.execute.return_value = MagicMock(
            data=[{"event_participation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"}]
        )

        result = remove_participants(event_id="35b43254-4e21-459f-b729-4cb3966cf322", participation_ids=["a1b2c3d4-e5f6-7890-abcd-ef1234567890", "b2c3d4e5-f6a7-8901-bcde-f12345678901"])  # first is host

        # Verify neq("role", "Host") was called
        mock_supabase.table.return_value.delete.return_value.eq.return_value.in_.return_value.neq.assert_called_with("role", "Host")
        assert result == 1


class TestGetParticipantsEndpoint:
    """Tests for GET /api/v1/events/{event_id}/participants endpoint."""

    def test_returns_participants_when_user_is_host(self, mock_supabase, mock_person_service):
        """Returns participant list when authenticated user is host."""
        with patch("app.core.supabase.create_client", return_value=mock_supabase):
            with patch("app.core.auth.get_current_user") as mock_auth:
                mock_user = MagicMock()
                mock_user.user.id = "user-uuid-123"
                mock_user.user.email = "test@example.com"
                mock_auth.return_value = mock_user
                with patch("app.services.event_service.get_event_by_id", return_value={"event_id": "35b43254-4e21-459f-b729-4cb3966cf322"}):
                    with patch("app.services.event_service.is_user_host", return_value=True):
                        with patch("app.services.event_service.get_event_participants") as mock_get:
                            mock_get.return_value = {
                                "participants": [
                                    {
                                        "event_participation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                        "status": "Accepted",
                                        "created_at": "2026-04-20T14:30:00Z",
                                        "person": {
                                            "person_id": "c1d2e3f4-a5b6-7890-cdef-123456789012",
                                            "first_name": "Max",
                                            "last_name": "Lehmann",
                                            "phone_number": "+49 170 1234567",
                                        },
                                    }
                                ],
                                "counts": {"accepted": 1, "declined": 0, "pending": 0},
                            }

                            from app.main import app
                            client = TestClient(app)
                            response = client.get(
                                "/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/participants",
                                headers={"Authorization": "Bearer test-token"},
                            )

                            assert response.status_code == 200
                            data = response.json()
                            assert len(data["participants"]) == 1
                            assert data["counts"]["accepted"] == 1

    def test_returns_403_when_user_is_not_host(self, mock_supabase, mock_person_service):
        """Returns 403 when authenticated user is not host."""
        with patch("app.core.supabase.create_client", return_value=mock_supabase):
            with patch("app.core.auth.get_current_user") as mock_auth:
                mock_user = MagicMock()
                mock_user.user.id = "user-uuid-123"
                mock_user.user.email = "test@example.com"
                mock_auth.return_value = mock_user
                with patch("app.services.event_service.get_event_by_id", return_value={"event_id": "35b43254-4e21-459f-b729-4cb3966cf322"}):
                    with patch("app.services.event_service.is_user_host", return_value=False):
                        from app.main import app
                        client = TestClient(app)
                        response = client.get(
                            "/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/participants",
                            headers={"Authorization": "Bearer test-token"},
                        )

                        assert response.status_code == 403

    def test_returns_404_when_event_not_found(self, mock_supabase, mock_person_service):
        """Returns 404 when event does not exist."""
        with patch("app.core.supabase.create_client", return_value=mock_supabase):
            with patch("app.core.auth.get_current_user") as mock_auth:
                mock_user = MagicMock()
                mock_user.user.id = "user-uuid-123"
                mock_user.user.email = "test@example.com"
                mock_auth.return_value = mock_user
                with patch("app.services.event_service.get_event_by_id", return_value=None):
                    from app.main import app
                    client = TestClient(app)
                    response = client.get(
                        "/api/v1/events/00000000-0000-0000-0000-000000000999/participants",
                        headers={"Authorization": "Bearer test-token"},
                    )

                    assert response.status_code == 404


class TestDeleteParticipantsEndpoint:
    """Tests for DELETE /api/v1/events/{event_id}/participants endpoint."""

    def test_removes_participants_when_user_is_host(self, mock_supabase, mock_person_service):
        """Removes participants when authenticated user is host."""
        with patch("app.core.supabase.create_client", return_value=mock_supabase):
            with patch("app.core.auth.get_current_user") as mock_auth:
                mock_user = MagicMock()
                mock_user.user.id = "user-uuid-123"
                mock_user.user.email = "test@example.com"
                mock_auth.return_value = mock_user
                with patch("app.services.event_service.get_event_by_id", return_value={"event_id": "35b43254-4e21-459f-b729-4cb3966cf322"}):
                    with patch("app.services.event_service.is_user_host", return_value=True):
                        with patch("app.services.event_service.remove_participants", return_value=2):
                            from app.main import app
                            client = TestClient(app)
                            response = client.request(
                                "DELETE",
                                "/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/participants",
                                headers={"Authorization": "Bearer test-token"},
                                json={"participation_ids": ["b2c3d4e5-f6a7-8901-bcde-f12345678901", "c3d4e5f6-a7b8-9012-cdef-234567890123"]},
                            )

                            assert response.status_code == 200
                            assert response.json()["removed_count"] == 2

    def test_returns_403_when_user_is_not_host(self, mock_supabase, mock_person_service):
        """Returns 403 when authenticated user is not host."""
        with patch("app.core.supabase.create_client", return_value=mock_supabase):
            with patch("app.core.auth.get_current_user") as mock_auth:
                mock_user = MagicMock()
                mock_user.user.id = "user-uuid-123"
                mock_user.user.email = "test@example.com"
                mock_auth.return_value = mock_user
                with patch("app.services.event_service.get_event_by_id", return_value={"event_id": "35b43254-4e21-459f-b729-4cb3966cf322"}):
                    with patch("app.services.event_service.is_user_host", return_value=False):
                        from app.main import app
                        client = TestClient(app)
                        response = client.request(
                            "DELETE",
                            "/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/participants",
                            headers={"Authorization": "Bearer test-token"},
                            json={"participation_ids": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"]},
                        )

                        assert response.status_code == 403

    def test_returns_404_when_event_not_found(self, mock_supabase, mock_person_service):
        """Returns 404 when event does not exist."""
        with patch("app.core.supabase.create_client", return_value=mock_supabase):
            with patch("app.core.auth.get_current_user") as mock_auth:
                mock_user = MagicMock()
                mock_user.user.id = "user-uuid-123"
                mock_user.user.email = "test@example.com"
                mock_auth.return_value = mock_user
                with patch("app.services.event_service.get_event_by_id", return_value=None):
                    from app.main import app
                    client = TestClient(app)
                    response = client.request(
                        "DELETE",
                        "/api/v1/events/00000000-0000-0000-0000-000000000999/participants",
                        headers={"Authorization": "Bearer test-token"},
                        json={"participation_ids": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"]},
                    )

                    assert response.status_code == 404