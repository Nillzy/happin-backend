"""Tests for event soft-delete: schema, service, and endpoint."""

from datetime import datetime
from unittest.mock import MagicMock, patch

_mock_supabase = MagicMock()

with patch("supabase.create_client", return_value=_mock_supabase):
    from fastapi.testclient import TestClient
    from app.main import app

client = TestClient(app)


def test_event_list_item_schema_has_is_deleted():
    """EventListItem has is_deleted (default False) and deleted_at (default None)."""
    from app.schemas.events import EventListItem
    item = EventListItem(
        event_id="abc",
        title="Test",
        starts_at=datetime(2027, 1, 1),
        is_public=True,
        is_free=True,
        participant_count=0,
    )
    assert item.is_deleted is False
    assert item.deleted_at is None


def test_event_list_item_schema_with_deleted():
    """EventListItem accepts explicit is_deleted=True and deleted_at values."""
    from app.schemas.events import EventListItem
    item = EventListItem(
        event_id="abc",
        title="Test",
        starts_at=datetime(2027, 1, 1),
        is_public=True,
        is_free=True,
        participant_count=0,
        is_deleted=True,
        deleted_at=datetime(2027, 1, 2),
    )
    assert item.is_deleted is True
    assert item.deleted_at == datetime(2027, 1, 2)


def test_event_detail_response_inherits_deleted_fields():
    """EventDetailResponse inherits is_deleted and deleted_at from EventListItem."""
    from app.schemas.events import EventDetailResponse
    detail = EventDetailResponse(
        event_id="xyz",
        title="Detail Test",
        starts_at=datetime(2027, 6, 1),
        is_public=False,
        is_free=True,
        participant_count=0,
        media_urls=[],
        is_deleted=True,
        deleted_at=datetime(2027, 5, 1),
    )
    assert detail.is_deleted is True
    assert detail.deleted_at == datetime(2027, 5, 1)


def test_delete_event_raises_if_not_host():
    """delete_event() raises PermissionError if caller is not the host."""
    from unittest.mock import patch as p2, MagicMock as MM

    mock_sb = MM()
    # Host check: not found
    host_chain = MM()
    host_chain.execute.return_value = MM(data=None)
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value = host_chain

    with p2("app.services.event_service.get_supabase_for_user", return_value=mock_sb):
        from app.services.event_service import delete_event
        import pytest
        with pytest.raises(PermissionError):
            delete_event("event-1", "person-1", "token")


def test_delete_event_raises_if_too_close_to_start():
    """delete_event() raises ValueError('too_close_to_start') if event starts in < 48h."""
    from datetime import timedelta, timezone
    from unittest.mock import patch as p2, MagicMock as MM
    import pytest

    starts_soon = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    with p2("app.services.event_service.get_supabase_for_user") as mock_get:
        mock_sb = MM()
        mock_get.return_value = mock_sb

        host_exec_result = MM(data={"event_host_id": "h1"})
        event_exec_result = MM(data={"starts_at": starts_soon, "deleted_at": None})

        def table_side_effect(table_name):
            t = MM()
            if table_name == "event_host":
                # chain: .select().eq("event_id").eq("person_id").maybe_single().execute()
                execute_mock = MM()
                execute_mock.execute.return_value = host_exec_result
                eq2 = MM()
                eq2.maybe_single.return_value = execute_mock
                eq1 = MM()
                eq1.eq.return_value = eq2
                sel = MM()
                sel.eq.return_value = eq1
                t.select.return_value = sel
            elif table_name == "event":
                # chain: .select().eq("event_id").maybe_single().execute()
                execute_mock = MM()
                execute_mock.execute.return_value = event_exec_result
                eq1 = MM()
                eq1.maybe_single.return_value = execute_mock
                sel = MM()
                sel.eq.return_value = eq1
                t.select.return_value = sel
                # handle .update().eq().execute()
                t.update.return_value.eq.return_value.execute.return_value = MM()
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services import event_service
        with pytest.raises(ValueError, match="too_close_to_start"):
            event_service.delete_event("event-1", "person-1", "token")


def test_delete_event_raises_if_already_deleted():
    """delete_event() raises ValueError('already_deleted') if deleted_at is already set."""
    from datetime import timedelta, timezone
    from unittest.mock import patch as p2, MagicMock as MM
    import pytest

    starts_future = (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat()

    with p2("app.services.event_service.get_supabase_for_user") as mock_get:
        mock_sb = MM()
        mock_get.return_value = mock_sb

        def table_side_effect(table_name):
            t = MM()
            if table_name == "event_host":
                execute_mock = MM()
                execute_mock.execute.return_value = MM(data={"event_host_id": "h1"})
                eq2 = MM()
                eq2.maybe_single.return_value = execute_mock
                eq1 = MM()
                eq1.eq.return_value = eq2
                sel = MM()
                sel.eq.return_value = eq1
                t.select.return_value = sel
            elif table_name == "event":
                execute_mock = MM()
                execute_mock.execute.return_value = MM(data={"starts_at": starts_future, "deleted_at": "2026-05-17T10:00:00+00:00"})
                eq1 = MM()
                eq1.maybe_single.return_value = execute_mock
                sel = MM()
                sel.eq.return_value = eq1
                t.select.return_value = sel
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services import event_service
        with pytest.raises(ValueError, match="already_deleted"):
            event_service.delete_event("event-1", "person-1", "token")


def test_delete_event_raises_if_event_not_found():
    """delete_event() raises ValueError('event_not_found') if event does not exist."""
    from unittest.mock import patch as p2, MagicMock as MM
    import pytest

    with p2("app.services.event_service.get_supabase_for_user") as mock_get:
        mock_sb = MM()
        mock_get.return_value = mock_sb

        def table_side_effect(table_name):
            t = MM()
            if table_name == "event_host":
                execute_mock = MM()
                execute_mock.execute.return_value = MM(data={"event_host_id": "h1"})
                eq2 = MM()
                eq2.maybe_single.return_value = execute_mock
                eq1 = MM()
                eq1.eq.return_value = eq2
                sel = MM()
                sel.eq.return_value = eq1
                t.select.return_value = sel
            elif table_name == "event":
                execute_mock = MM()
                execute_mock.execute.return_value = MM(data=None)
                eq1 = MM()
                eq1.maybe_single.return_value = execute_mock
                sel = MM()
                sel.eq.return_value = eq1
                t.select.return_value = sel
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services import event_service
        with pytest.raises(ValueError, match="event_not_found"):
            event_service.delete_event("event-1", "person-1", "token")


def test_delete_event_success():
    """delete_event() calls UPDATE when all checks pass."""
    from datetime import timedelta, timezone
    from unittest.mock import patch as p2, MagicMock as MM

    starts_future = (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat()

    with p2("app.services.event_service.get_supabase_for_user") as mock_get:
        mock_sb = MM()
        mock_get.return_value = mock_sb

        event_tables = []

        def table_side_effect(table_name):
            t = MM()
            if table_name == "event_host":
                execute_mock = MM()
                execute_mock.execute.return_value = MM(data={"event_host_id": "h1"})
                eq2 = MM()
                eq2.maybe_single.return_value = execute_mock
                eq1 = MM()
                eq1.eq.return_value = eq2
                sel = MM()
                sel.eq.return_value = eq1
                t.select.return_value = sel
            elif table_name == "event":
                execute_mock = MM()
                execute_mock.execute.return_value = MM(data={"starts_at": starts_future, "deleted_at": None})
                eq1 = MM()
                eq1.maybe_single.return_value = execute_mock
                sel = MM()
                sel.eq.return_value = eq1
                t.select.return_value = sel
                t.update.return_value.eq.return_value.execute.return_value = MM()
                event_tables.append(t)
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services import event_service
        event_service.delete_event("event-1", "person-1", "token")

        # Verify UPDATE was called on the event table mock
        assert len(event_tables) >= 1
        event_tables[-1].update.assert_called_once()


def test_delete_event_endpoint_returns_204():
    """DELETE /api/v1/events/{id} returns 204 when host deletes a valid event."""
    from unittest.mock import patch as p2, MagicMock as MM

    with p2("app.services.event_service.delete_event") as mock_del, \
         p2("app.services.person_service.get_or_create_person") as mock_person, \
         p2("app.core.auth.get_current_user") as mock_user:

        mock_user.return_value = MM(user=MM(id="uid-1", email="a@b.de"))
        mock_person.return_value = {"person_id": "p-1"}
        mock_del.return_value = None  # void

        resp = client.delete(
            "/api/v1/events/event-1",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 204


def test_delete_event_endpoint_returns_400_when_too_close():
    """DELETE /api/v1/events/{id} returns 400 when event starts in < 48h."""
    from unittest.mock import patch as p2, MagicMock as MM

    with p2("app.services.event_service.delete_event") as mock_del, \
         p2("app.services.person_service.get_or_create_person") as mock_person, \
         p2("app.core.auth.get_current_user") as mock_user:

        mock_user.return_value = MM(user=MM(id="uid-1", email="a@b.de"))
        mock_person.return_value = {"person_id": "p-1"}
        mock_del.side_effect = ValueError("too_close_to_start")

        resp = client.delete(
            "/api/v1/events/event-1",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 400
        assert "48" in resp.json()["detail"]


def test_delete_event_endpoint_returns_403_when_not_host():
    """DELETE /api/v1/events/{id} returns 403 when caller is not the host."""
    from unittest.mock import patch as p2, MagicMock as MM

    with p2("app.services.event_service.delete_event") as mock_del, \
         p2("app.services.person_service.get_or_create_person") as mock_person, \
         p2("app.core.auth.get_current_user") as mock_user:

        mock_user.return_value = MM(user=MM(id="uid-1", email="a@b.de"))
        mock_person.return_value = {"person_id": "p-1"}
        mock_del.side_effect = PermissionError("not_host")

        resp = client.delete(
            "/api/v1/events/event-1",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 403
