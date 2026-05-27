"""Tests for waitlist_service."""

from unittest.mock import MagicMock, patch


def _make_supabase(data=None, count=0):
    """Build a mock Supabase client where every chained call returns the mock."""
    sb = MagicMock()
    result = MagicMock()
    if data is None:
        result.data = []
    elif isinstance(data, list):
        result.data = data
    else:
        result.data = [data]
    result.count = count
    sb.table.return_value = sb
    sb.select.return_value = sb
    sb.eq.return_value = sb
    sb.in_.return_value = sb
    sb.lt.return_value = sb
    sb.is_.return_value = sb
    sb.order.return_value = sb
    sb.limit.return_value = sb
    sb.insert.return_value = sb
    sb.update.return_value = sb
    sb.delete.return_value = sb
    sb.upsert.return_value = sb
    sb.execute.return_value = result
    return sb, result


class TestLeaveWaitlist:
    def test_raises_not_on_waitlist_if_no_entry(self):
        with patch("app.services.waitlist_service.get_supabase_for_user") as mock_user:
            sb, result = _make_supabase(data=None)
            mock_user.return_value = sb
            from app.services.waitlist_service import leave_waitlist
            try:
                leave_waitlist("event-id", "person-id", "token")
                assert False, "Should have raised"
            except ValueError as e:
                assert str(e) == "not_on_waitlist"

    def test_raises_not_on_waitlist_if_removed_status(self):
        with patch("app.services.waitlist_service.get_supabase_for_user") as mock_user:
            sb, result = _make_supabase(data={"waitlist_id": "wid", "status": "removed"})
            mock_user.return_value = sb
            from app.services.waitlist_service import leave_waitlist
            try:
                leave_waitlist("event-id", "person-id", "token")
                assert False, "Should have raised"
            except ValueError as e:
                assert str(e) == "not_on_waitlist"

    def test_raises_not_on_waitlist_if_expired_status(self):
        with patch("app.services.waitlist_service.get_supabase_for_user") as mock_user:
            sb, result = _make_supabase(data={"waitlist_id": "wid", "status": "expired"})
            mock_user.return_value = sb
            from app.services.waitlist_service import leave_waitlist
            try:
                leave_waitlist("event-id", "person-id", "token")
                assert False, "Should have raised"
            except ValueError as e:
                assert str(e) == "not_on_waitlist"

    def test_succeeds_for_waiting_status(self):
        with patch("app.services.waitlist_service.get_supabase_for_user") as mock_user:
            sb, result = _make_supabase(data={"waitlist_id": "wid", "status": "waiting"})
            mock_user.return_value = sb
            from app.services.waitlist_service import leave_waitlist
            leave_waitlist("event-id", "person-id", "token")  # Should not raise

    def test_succeeds_for_notified_status(self):
        with patch("app.services.waitlist_service.get_supabase_for_user") as mock_user:
            sb, result = _make_supabase(data={"waitlist_id": "wid", "status": "notified"})
            mock_user.return_value = sb
            from app.services.waitlist_service import leave_waitlist
            leave_waitlist("event-id", "person-id", "token")  # Should not raise


class TestGetWaitlistPosition:
    def test_raises_not_on_waitlist_if_no_entry(self):
        with patch("app.services.waitlist_service.get_supabase_for_user") as mock_user:
            sb, result = _make_supabase(data=None)
            mock_user.return_value = sb
            from app.services.waitlist_service import get_waitlist_position
            try:
                get_waitlist_position("event-id", "person-id", "token")
                assert False, "Should have raised"
            except ValueError as e:
                assert str(e) == "not_on_waitlist"

    def test_returns_position_1_when_no_one_ahead(self):
        with patch("app.services.waitlist_service.get_supabase_for_user") as mock_user, \
             patch("app.services.waitlist_service._get_position_count", return_value=0):
            sb = MagicMock()
            own_result = MagicMock()
            own_result.data = [{"joined_at": "2026-05-22T10:00:00+00:00", "status": "waiting"}]
            sb.table.return_value = sb
            sb.select.return_value = sb
            sb.eq.return_value = sb
            sb.in_.return_value = sb
            sb.limit.return_value = sb
            sb.execute.return_value = own_result
            mock_user.return_value = sb
            from app.services.waitlist_service import get_waitlist_position
            result = get_waitlist_position("event-id", "person-id", "token")
            assert result == 1

    def test_returns_position_3_when_two_ahead(self):
        with patch("app.services.waitlist_service.get_supabase_for_user") as mock_user, \
             patch("app.services.waitlist_service._get_position_count", return_value=2):
            sb = MagicMock()
            own_result = MagicMock()
            own_result.data = [{"joined_at": "2026-05-22T10:00:00+00:00", "status": "waiting"}]
            sb.table.return_value = sb
            sb.select.return_value = sb
            sb.eq.return_value = sb
            sb.in_.return_value = sb
            sb.limit.return_value = sb
            sb.execute.return_value = own_result
            mock_user.return_value = sb
            from app.services.waitlist_service import get_waitlist_position
            result = get_waitlist_position("event-id", "person-id", "token")
            assert result == 3


class TestExpireStalePromotions:
    def test_returns_zero_when_no_stale_entries(self):
        with patch("app.services.waitlist_service.get_supabase_admin") as mock_admin:
            sb, result = _make_supabase(data=[])
            mock_admin.return_value = sb
            from app.services.waitlist_service import expire_stale_promotions
            count = expire_stale_promotions("event-id")
            assert count == 0

    def test_returns_count_of_expired_entries(self):
        with patch("app.services.waitlist_service.get_supabase_admin") as mock_admin:
            sb = MagicMock()
            stale_result = MagicMock()
            stale_result.data = [{"waitlist_id": "w1"}, {"waitlist_id": "w2"}]
            update_result = MagicMock()
            update_result.data = [{}]

            call_count = [0]
            def execute():
                call_count[0] += 1
                if call_count[0] == 1:
                    return stale_result
                return update_result

            sb.table.return_value = sb
            sb.select.return_value = sb
            sb.eq.return_value = sb
            sb.lt.return_value = sb
            sb.update.return_value = sb
            sb.execute.side_effect = lambda: execute()
            mock_admin.return_value = sb

            from app.services.waitlist_service import expire_stale_promotions
            count = expire_stale_promotions("event-id")
            assert count == 2


class TestPromoteNext:
    def test_does_nothing_if_no_max_capacity(self):
        with patch("app.services.waitlist_service.get_supabase_admin") as mock_admin, \
             patch("app.services.waitlist_service.expire_stale_promotions", return_value=0):
            sb = MagicMock()
            event_result = MagicMock()
            event_result.data = [{
                "max_capacity": None, "is_free": True,
                "waitlist_promotion_hours": 24, "title": "T",
                "invitation_link": "https://happin.fun/t"
            }]
            sb.table.return_value = sb
            sb.select.return_value = sb
            sb.eq.return_value = sb
            sb.limit.return_value = sb
            sb.execute.return_value = event_result
            mock_admin.return_value = sb
            from app.services.waitlist_service import promote_next
            promote_next("event-id")  # should not raise

    def test_does_nothing_if_event_still_full(self):
        with patch("app.services.waitlist_service.get_supabase_admin") as mock_admin, \
             patch("app.services.waitlist_service.expire_stale_promotions", return_value=0), \
             patch("app.services.waitlist_service.booking_service") as mock_bs, \
             patch("app.services.waitlist_service._count_notified", return_value=0):
            sb = MagicMock()
            event_result = MagicMock()
            event_result.data = [{
                "max_capacity": 10, "is_free": True,
                "waitlist_promotion_hours": 24, "title": "T",
                "invitation_link": "https://happin.fun/t"
            }]
            sb.table.return_value = sb
            sb.select.return_value = sb
            sb.eq.return_value = sb
            sb.limit.return_value = sb
            sb.execute.return_value = event_result
            mock_admin.return_value = sb
            mock_bs.count_event_tickets.return_value = 10
            mock_bs.count_pending_order_quantity.return_value = 0
            from app.services.waitlist_service import promote_next
            promote_next("event-id")  # should not raise or create tickets

    def test_does_nothing_if_queue_empty(self):
        with patch("app.services.waitlist_service.get_supabase_admin") as mock_admin, \
             patch("app.services.waitlist_service.expire_stale_promotions", return_value=0), \
             patch("app.services.waitlist_service.booking_service") as mock_bs, \
             patch("app.services.waitlist_service._count_notified", return_value=0):
            sb = MagicMock()
            event_result = MagicMock()
            event_result.data = [{
                "max_capacity": 10, "is_free": True,
                "waitlist_promotion_hours": 24, "title": "T",
                "invitation_link": "https://happin.fun/t"
            }]
            no_entry_result = MagicMock()
            no_entry_result.data = []

            call_idx = [0]
            results = [event_result, no_entry_result]
            def execute():
                r = results[min(call_idx[0], len(results) - 1)]
                call_idx[0] += 1
                return r

            sb.table.return_value = sb
            sb.select.return_value = sb
            sb.eq.return_value = sb
            sb.order.return_value = sb
            sb.limit.return_value = sb
            sb.execute.side_effect = lambda: execute()
            mock_admin.return_value = sb
            mock_bs.count_event_tickets.return_value = 9
            mock_bs.count_pending_order_quantity.return_value = 0

            from app.services.waitlist_service import promote_next
            promote_next("event-id")  # should not raise
