"""Tests for event cancellation: schema, service, and endpoint."""

from datetime import datetime
from unittest.mock import MagicMock, patch

_mock_supabase = MagicMock()

with patch("supabase.create_client", return_value=_mock_supabase):
    from fastapi.testclient import TestClient
    from app.main import app

client = TestClient(app)


def test_event_list_item_schema_has_is_cancelled():
    """EventListItem has is_cancelled (default False) and cancelled_at (default None)."""
    from app.schemas.events import EventListItem
    item = EventListItem(
        event_id="abc",
        title="Test",
        starts_at=datetime(2027, 1, 1),
        is_public=True,
        is_free=True,
        participant_count=0,
    )
    assert item.is_cancelled is False
    assert item.cancelled_at is None


def test_event_list_item_schema_with_cancelled():
    """EventListItem accepts explicit is_cancelled=True and cancelled_at values."""
    from app.schemas.events import EventListItem
    item = EventListItem(
        event_id="abc",
        title="Test",
        starts_at=datetime(2027, 1, 1),
        is_public=True,
        is_free=True,
        participant_count=0,
        is_cancelled=True,
        cancelled_at=datetime(2027, 1, 2),
    )
    assert item.is_cancelled is True
    assert item.cancelled_at == datetime(2027, 1, 2)


def test_event_detail_response_inherits_cancelled_fields():
    """EventDetailResponse inherits is_cancelled and cancelled_at from EventListItem."""
    from app.schemas.events import EventDetailResponse
    detail = EventDetailResponse(
        event_id="xyz",
        title="Detail Test",
        starts_at=datetime(2027, 6, 1),
        is_public=False,
        is_free=True,
        participant_count=0,
        media_urls=[],
        is_cancelled=True,
        cancelled_at=datetime(2027, 5, 1),
    )
    assert detail.is_cancelled is True
    assert detail.cancelled_at == datetime(2027, 5, 1)


def test_refund_summary_schema_defaults():
    """RefundSummary has the four expected fields."""
    from app.schemas.events import RefundSummary
    summary = RefundSummary(
        refunded_count=0,
        failed_count=0,
        failed_order_ids=[],
        skipped_count=0,
    )
    assert summary.refunded_count == 0
    assert summary.failed_count == 0
    assert summary.failed_order_ids == []
    assert summary.skipped_count == 0


def test_cancel_event_raises_if_not_host():
    """cancel_event() raises PermissionError if caller is not the host."""
    from unittest.mock import patch as p2, MagicMock as MM

    mock_sb = MM()
    host_chain = MM()
    host_chain.execute.return_value = MM(data=None)
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value = host_chain

    with p2("app.services.event_service.get_supabase_for_user", return_value=mock_sb):
        from app.services.event_service import cancel_event
        import pytest
        with pytest.raises(PermissionError):
            cancel_event("event-1", "person-1", "token")


def test_cancel_event_works_close_to_start():
    """cancel_event() works even if event starts in < 48h (no 48h-Sperre mehr)."""
    from datetime import timedelta, timezone
    from unittest.mock import patch as p2, MagicMock as MM

    starts_soon = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    with p2("app.services.event_service.get_supabase_for_user") as mock_get, \
         p2("app.services.event_service.get_supabase") as mock_get_admin, \
         p2("app.services.event_service._refund_all_paid_orders") as mock_refund:
        mock_sb = MM()
        mock_get.return_value = mock_sb
        mock_get_admin.return_value = MM()
        from app.schemas.events import RefundSummary
        mock_refund.return_value = RefundSummary(
            refunded_count=0, failed_count=0, failed_order_ids=[], skipped_count=0
        )

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
                execute_mock.execute.return_value = MM(data={"starts_at": starts_soon, "cancelled_at": None})
                eq1 = MM()
                eq1.maybe_single.return_value = execute_mock
                sel = MM()
                sel.eq.return_value = eq1
                t.select.return_value = sel
                t.update.return_value.eq.return_value.execute.return_value = MM()
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services import event_service
        result = event_service.cancel_event("event-1", "person-1", "token")
        assert result.refunded_count == 0


def test_cancel_event_raises_if_already_cancelled():
    """cancel_event() raises ValueError('already_cancelled') if cancelled_at is already set."""
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
                execute_mock.execute.return_value = MM(data={"starts_at": starts_future, "cancelled_at": "2026-05-17T10:00:00+00:00"})
                eq1 = MM()
                eq1.maybe_single.return_value = execute_mock
                sel = MM()
                sel.eq.return_value = eq1
                t.select.return_value = sel
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services import event_service
        with pytest.raises(ValueError, match="already_cancelled"):
            event_service.cancel_event("event-1", "person-1", "token")


def test_cancel_event_raises_if_event_not_found():
    """cancel_event() raises ValueError('event_not_found') if event does not exist."""
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
            event_service.cancel_event("event-1", "person-1", "token")


def test_cancel_event_success_returns_refund_summary():
    """cancel_event() calls UPDATE and returns RefundSummary on success."""
    from datetime import timedelta, timezone
    from unittest.mock import patch as p2, MagicMock as MM

    starts_future = (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat()

    with p2("app.services.event_service.get_supabase_for_user") as mock_get, \
         p2("app.services.event_service._refund_all_paid_orders") as mock_refund:
        mock_sb = MM()
        mock_get.return_value = mock_sb

        from app.schemas.events import RefundSummary
        mock_refund.return_value = RefundSummary(
            refunded_count=2, failed_count=0, failed_order_ids=[], skipped_count=0
        )

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
                execute_mock.execute.return_value = MM(data={"starts_at": starts_future, "cancelled_at": None})
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
        result = event_service.cancel_event("event-1", "person-1", "token")

        assert len(event_tables) >= 1
        event_tables[-1].update.assert_called_once()
        assert result.refunded_count == 2
        assert result.failed_count == 0


def test_cancel_event_endpoint_returns_200_with_summary():
    """POST /api/v1/events/{id}/cancel returns 200 with RefundSummary."""
    from unittest.mock import patch as p2, MagicMock as MM

    with p2("app.services.event_service.cancel_event") as mock_cancel, \
         p2("app.services.person_service.get_or_create_person") as mock_person, \
         p2("app.core.auth.get_current_user") as mock_user:

        mock_user.return_value = MM(user=MM(id="uid-1", email="a@b.de"))
        mock_person.return_value = {"person_id": "p-1"}
        from app.schemas.events import RefundSummary
        mock_cancel.return_value = RefundSummary(
            refunded_count=2, failed_count=0, failed_order_ids=[], skipped_count=1
        )

        resp = client.post(
            "/api/v1/events/event-1/cancel",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["refunded_count"] == 2
        assert body["failed_count"] == 0
        assert body["skipped_count"] == 1


def test_cancel_event_endpoint_returns_400_when_already_cancelled():
    """POST /api/v1/events/{id}/cancel returns 400 when event is already cancelled."""
    from unittest.mock import patch as p2, MagicMock as MM

    with p2("app.services.event_service.cancel_event") as mock_cancel, \
         p2("app.services.person_service.get_or_create_person") as mock_person, \
         p2("app.core.auth.get_current_user") as mock_user:

        mock_user.return_value = MM(user=MM(id="uid-1", email="a@b.de"))
        mock_person.return_value = {"person_id": "p-1"}
        mock_cancel.side_effect = ValueError("already_cancelled")

        resp = client.post(
            "/api/v1/events/event-1/cancel",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 400
        assert "abgesagt" in resp.json()["detail"].lower()


def test_cancel_event_endpoint_returns_403_when_not_host():
    """POST /api/v1/events/{id}/cancel returns 403 when caller is not the host."""
    from unittest.mock import patch as p2, MagicMock as MM

    with p2("app.services.event_service.cancel_event") as mock_cancel, \
         p2("app.services.person_service.get_or_create_person") as mock_person, \
         p2("app.core.auth.get_current_user") as mock_user:

        mock_user.return_value = MM(user=MM(id="uid-1", email="a@b.de"))
        mock_person.return_value = {"person_id": "p-1"}
        mock_cancel.side_effect = PermissionError("not_host")

        resp = client.post(
            "/api/v1/events/event-1/cancel",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 403
