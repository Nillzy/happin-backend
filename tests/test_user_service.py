"""Behavior-driven tests for user_service.

Tests cover:
- get_user_stats: aggregation across multiple Supabase queries
- get_user_events: role filtering, period filtering, paid-event detection, dedup
- delete_user: cascading delete order + auth-only fallback
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services import user_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exec(data=None, count=None):
    """Helper that returns a MagicMock with .execute() yielding given data/count."""
    m = MagicMock()
    m.execute.return_value = MagicMock(data=data, count=count)
    return m


# ---------------------------------------------------------------------------
# get_user_stats
# ---------------------------------------------------------------------------


class TestGetUserStats:
    """Tests for user_service.get_user_stats."""

    @patch("app.services.user_service.get_supabase")
    def test_should_return_zeros_when_user_has_no_events(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        # event_host -> no events
        # event_participation -> no participation
        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[], count=0
        )
        attended_q = MagicMock()
        attended_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[], count=0
        )
        sb.table.side_effect = lambda name: {
            "event_host": host_q,
            "event_participation": attended_q,
        }[name]

        stats = user_service.get_user_stats("person-1")

        assert stats == {
            "events_attended": 0,
            "events_created": 0,
            "tickets_total": 0,
            "participants_total": 0,
        }

    @patch("app.services.user_service.get_supabase")
    def test_should_count_hosted_events_and_participants(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-1"}, {"event_id": "evt-2"}],
            count=2,
        )
        parts_q = MagicMock()
        parts_q.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[], count=15
        )
        parts_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[], count=3
        )

        def table(name):
            if name == "event_host":
                return host_q
            return parts_q

        sb.table.side_effect = table

        stats = user_service.get_user_stats("person-1")

        assert stats["events_created"] == 2
        assert stats["participants_total"] == 15
        assert stats["events_attended"] == 3
        assert stats["tickets_total"] == 3

    @patch("app.services.user_service.get_supabase")
    def test_should_skip_participants_query_when_no_hosted_events(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[], count=0
        )
        parts_q = MagicMock()
        parts_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[], count=0
        )

        def table(name):
            return host_q if name == "event_host" else parts_q

        sb.table.side_effect = table

        stats = user_service.get_user_stats("person-1")

        # When no hosted events, the .in_() chain for participants must NOT be called
        parts_q.select.return_value.in_.assert_not_called()
        assert stats["participants_total"] == 0

    @patch("app.services.user_service.get_supabase")
    def test_should_handle_none_count_as_zero(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=None, count=None
        )
        parts_q = MagicMock()
        parts_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=None, count=None
        )

        def table(name):
            return host_q if name == "event_host" else parts_q

        sb.table.side_effect = table

        stats = user_service.get_user_stats("person-1")

        assert stats["events_created"] == 0
        assert stats["events_attended"] == 0

    @patch("app.services.user_service.get_supabase")
    def test_should_raise_when_supabase_throws(self, mock_get_sb):
        sb = MagicMock()
        sb.table.side_effect = RuntimeError("DB down")
        mock_get_sb.return_value = sb

        with pytest.raises(RuntimeError, match="DB down"):
            user_service.get_user_stats("person-1")


# ---------------------------------------------------------------------------
# get_user_events
# ---------------------------------------------------------------------------


class TestGetUserEvents:
    """Tests for user_service.get_user_events."""

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_return_empty_list_when_user_has_no_events(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        part_q = MagicMock()
        part_q.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        def table(name):
            return host_q if name == "event_host" else part_q

        sb.table.side_effect = table

        result = user_service.get_user_events("person-1", "tok")

        assert result == []

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_return_hosted_upcoming_events_when_role_is_organizer(
        self, mock_get_sb
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        # event_host lookup
        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-1"}]
        )

        # event query (gte for upcoming)
        event_q = MagicMock()
        event_chain = event_q.select.return_value.in_.return_value
        event_chain.gte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "event_id": "evt-1",
                    "starts_at": "2026-09-01T18:00:00Z",
                    "ticket": [],
                }
            ]
        )

        # ticket_option (paid detection)
        opts_q = MagicMock()
        opts_q.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[]
        )

        # ticket_order (revenue)
        orders_q = MagicMock()
        orders_q.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        def table(name):
            return {
                "event_host": host_q,
                "event": event_q,
                "ticket_option": opts_q,
                "ticket_order": orders_q,
            }[name]

        sb.table.side_effect = table

        result = user_service.get_user_events(
            "person-1", "tok", role="organizer", period="upcoming"
        )

        assert len(result) == 1
        assert result[0]["is_host"] is True
        assert result[0]["ticket_revenue_cents"] == 0

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_flag_event_as_paid_when_ticket_option_has_price(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-paid"}]
        )

        event_q = MagicMock()
        event_chain = event_q.select.return_value.in_.return_value
        event_chain.gte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "event_id": "evt-paid",
                    "starts_at": "2026-09-01T18:00:00Z",
                    "ticket": [],
                }
            ]
        )

        opts_q = MagicMock()
        opts_q.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-paid", "price": 10.0}]
        )

        orders_q = MagicMock()
        orders_q.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        def table(name):
            return {
                "event_host": host_q,
                "event": event_q,
                "ticket_option": opts_q,
                "ticket_order": orders_q,
            }[name]

        sb.table.side_effect = table

        result = user_service.get_user_events("person-1", "tok", role="organizer")

        assert result[0]["is_free"] is False

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_use_real_revenue_from_paid_orders_when_available(
        self, mock_get_sb
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-1"}]
        )

        event_q = MagicMock()
        event_chain = event_q.select.return_value.in_.return_value
        event_chain.gte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "event_id": "evt-1",
                    "starts_at": "2026-09-01T18:00:00Z",
                    "ticket": [{"ticket_option": {"price": 5}}],
                }
            ]
        )

        opts_q = MagicMock()
        opts_q.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[]
        )

        orders_q = MagicMock()
        orders_q.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {"event_id": "evt-1", "amount_total_cents": 1000},
                {"event_id": "evt-1", "amount_total_cents": 500},
            ]
        )

        def table(name):
            return {
                "event_host": host_q,
                "event": event_q,
                "ticket_option": opts_q,
                "ticket_order": orders_q,
            }[name]

        sb.table.side_effect = table

        result = user_service.get_user_events("person-1", "tok", role="organizer")

        # Real revenue (1500) takes precedence over catalog estimate
        assert result[0]["ticket_revenue_cents"] == 1500

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_fallback_to_catalog_estimate_when_no_orders_exist(
        self, mock_get_sb
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-1"}]
        )

        event_q = MagicMock()
        event_chain = event_q.select.return_value.in_.return_value
        event_chain.gte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "event_id": "evt-1",
                    "starts_at": "2026-09-01T18:00:00Z",
                    "ticket": [
                        {"ticket_option": {"price": 10}},
                        {"ticket_option": {"price": 5}},
                    ],
                }
            ]
        )

        opts_q = MagicMock()
        opts_q.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[]
        )

        orders_q = MagicMock()
        orders_q.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        def table(name):
            return {
                "event_host": host_q,
                "event": event_q,
                "ticket_option": opts_q,
                "ticket_order": orders_q,
            }[name]

        sb.table.side_effect = table

        result = user_service.get_user_events("person-1", "tok", role="organizer")

        # Catalog estimate: (10 + 5) * 100 = 1500 cents
        assert result[0]["ticket_revenue_cents"] == 1500

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_return_attended_events_when_role_is_attendee(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        part_q = MagicMock()
        part_q.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-att-1"}]
        )

        event_q = MagicMock()
        event_chain = event_q.select.return_value.in_.return_value
        event_chain.gte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "event_id": "evt-att-1",
                    "starts_at": "2026-09-01T18:00:00Z",
                    "ticket": [],
                }
            ]
        )

        def table(name):
            return {
                "event_participation": part_q,
                "event": event_q,
            }[name]

        sb.table.side_effect = table

        result = user_service.get_user_events(
            "person-1", "tok", role="attendee", period="upcoming"
        )

        assert len(result) == 1
        assert result[0]["is_host"] is False

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_filter_past_events_when_period_is_past(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-1"}]
        )

        event_q = MagicMock()
        event_chain = event_q.select.return_value.in_.return_value
        # For past period, .lt() is used instead of .gte()
        event_chain.lt.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "event_id": "evt-1",
                    "starts_at": "2024-01-01T18:00:00Z",
                    "ticket": [],
                }
            ]
        )

        opts_q = MagicMock()
        opts_q.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[]
        )
        orders_q = MagicMock()
        orders_q.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        def table(name):
            return {
                "event_host": host_q,
                "event": event_q,
                "ticket_option": opts_q,
                "ticket_order": orders_q,
            }[name]

        sb.table.side_effect = table

        result = user_service.get_user_events(
            "person-1", "tok", role="organizer", period="past"
        )

        # .lt() must have been called for past period
        event_chain.lt.assert_called_once()
        assert len(result) == 1

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_deduplicate_when_user_is_both_host_and_attendee(
        self, mock_get_sb
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        # Same event-id returned via both role paths
        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-dup"}]
        )
        part_q = MagicMock()
        part_q.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-dup"}]
        )

        event_q = MagicMock()
        event_chain = event_q.select.return_value.in_.return_value
        event_chain.gte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "event_id": "evt-dup",
                    "starts_at": "2026-09-01T18:00:00Z",
                    "ticket": [],
                }
            ]
        )

        opts_q = MagicMock()
        opts_q.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[]
        )
        orders_q = MagicMock()
        orders_q.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        def table(name):
            return {
                "event_host": host_q,
                "event_participation": part_q,
                "event": event_q,
                "ticket_option": opts_q,
                "ticket_order": orders_q,
            }[name]

        sb.table.side_effect = table

        result = user_service.get_user_events("person-1", "tok")  # role=None → both

        # Despite appearing in both, event should be returned only once
        assert len(result) == 1
        assert result[0]["event_id"] == "evt-dup"

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_apply_offset_and_limit(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": f"evt-{i}"} for i in range(5)]
        )

        event_q = MagicMock()
        event_chain = event_q.select.return_value.in_.return_value
        event_chain.gte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "event_id": f"evt-{i}",
                    "starts_at": f"2026-09-0{i+1}T18:00:00Z",
                    "ticket": [],
                }
                for i in range(5)
            ]
        )

        opts_q = MagicMock()
        opts_q.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[]
        )
        orders_q = MagicMock()
        orders_q.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        def table(name):
            return {
                "event_host": host_q,
                "event": event_q,
                "ticket_option": opts_q,
                "ticket_order": orders_q,
            }[name]

        sb.table.side_effect = table

        result = user_service.get_user_events(
            "person-1", "tok", role="organizer", limit=2, offset=1
        )

        assert len(result) == 2

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_flag_attended_paid_event_as_not_free(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        part_q = MagicMock()
        part_q.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-att"}]
        )

        event_q = MagicMock()
        event_chain = event_q.select.return_value.in_.return_value
        event_chain.gte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "event_id": "evt-att",
                    "starts_at": "2026-09-01T18:00:00Z",
                    "ticket": [{"ticket_option": {"price": 25}}],
                }
            ]
        )

        def table(name):
            return {
                "event_participation": part_q,
                "event": event_q,
            }[name]

        sb.table.side_effect = table

        result = user_service.get_user_events("person-1", "tok", role="attendee")

        assert result[0]["is_free"] is False

    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_raise_when_supabase_query_fails(self, mock_get_sb):
        sb = MagicMock()
        sb.table.side_effect = RuntimeError("DB error")
        mock_get_sb.return_value = sb

        with pytest.raises(RuntimeError, match="DB error"):
            user_service.get_user_events("person-1", "tok")


# ---------------------------------------------------------------------------
# get_user_tickets
# ---------------------------------------------------------------------------


class TestGetUserTickets:
    """Tests for user_service.get_user_tickets (delegates to ticket_service)."""

    @patch("app.services.ticket_service.get_tickets_for_person")
    def test_should_delegate_to_ticket_service(self, mock_get_tickets):
        mock_get_tickets.return_value = {"tickets": [], "events": []}

        result = user_service.get_user_tickets("person-1", "tok")

        mock_get_tickets.assert_called_once_with("person-1", "tok")
        assert result == {"tickets": [], "events": []}

    @patch("app.services.ticket_service.get_tickets_for_person")
    def test_should_propagate_error_from_ticket_service(self, mock_get_tickets):
        mock_get_tickets.side_effect = RuntimeError("ticket service down")

        with pytest.raises(RuntimeError, match="ticket service down"):
            user_service.get_user_tickets("person-1", "tok")


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------


class TestDeleteUser:
    """Tests for user_service.delete_user."""

    @patch("app.services.user_service.get_supabase")
    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_delete_only_auth_when_no_person_record_exists(
        self, mock_sb_user, mock_sb_admin
    ):
        sb_user = MagicMock()
        sb_admin = MagicMock()
        mock_sb_user.return_value = sb_user
        mock_sb_admin.return_value = sb_admin

        # No person record
        person_q = MagicMock()
        person_q.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        sb_user.table.return_value = person_q

        user_service.delete_user("uid-x", "tok")

        sb_admin.auth.admin.delete_user.assert_called_once_with("uid-x")
        # Should NOT have deleted any rows from event_participation etc.
        person_q.delete.assert_not_called()

    @patch("app.services.user_service.get_supabase")
    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_cascade_delete_participations_events_person_and_auth(
        self, mock_sb_user, mock_sb_admin
    ):
        sb_user = MagicMock()
        sb_admin = MagicMock()
        mock_sb_user.return_value = sb_user
        mock_sb_admin.return_value = sb_admin

        person_q = MagicMock()
        person_q.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"person_id": "p-1"}
        )

        # event_participation delete
        part_q = MagicMock()
        part_q.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        # event_host SELECT -> hosted events
        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"event_id": "evt-1"}, {"event_id": "evt-2"}]
        )

        # event delete
        event_q = MagicMock()
        event_q.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        # person delete
        person_del_q = MagicMock()
        person_del_q.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        call_order: list[str] = []

        def table(name):
            call_order.append(name)
            if name == "person" and call_order.count("person") == 1:
                return person_q
            if name == "person":
                return person_del_q
            return {
                "event_participation": part_q,
                "event_host": host_q,
                "event": event_q,
            }[name]

        sb_user.table.side_effect = table

        user_service.delete_user("uid-x", "tok")

        # Participations deleted
        part_q.delete.assert_called_once()
        # Two hosted events deleted
        assert event_q.delete.call_count == 2
        # Person row deleted
        person_del_q.delete.assert_called_once()
        # Auth account removed last
        sb_admin.auth.admin.delete_user.assert_called_once_with("uid-x")

    @patch("app.services.user_service.get_supabase")
    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_handle_user_with_no_hosted_events(
        self, mock_sb_user, mock_sb_admin
    ):
        sb_user = MagicMock()
        sb_admin = MagicMock()
        mock_sb_user.return_value = sb_user
        mock_sb_admin.return_value = sb_admin

        person_q = MagicMock()
        person_q.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"person_id": "p-1"}
        )
        part_q = MagicMock()
        host_q = MagicMock()
        host_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        event_q = MagicMock()
        person_del_q = MagicMock()

        person_call_count = {"n": 0}

        def table(name):
            if name == "person":
                person_call_count["n"] += 1
                return person_q if person_call_count["n"] == 1 else person_del_q
            return {
                "event_participation": part_q,
                "event_host": host_q,
                "event": event_q,
            }[name]

        sb_user.table.side_effect = table

        user_service.delete_user("uid-x", "tok")

        # No events were deleted (loop body never executed)
        event_q.delete.assert_not_called()
        sb_admin.auth.admin.delete_user.assert_called_once()

    @patch("app.services.user_service.get_supabase")
    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_handle_missing_person_data_field(
        self, mock_sb_user, mock_sb_admin
    ):
        sb_user = MagicMock()
        sb_admin = MagicMock()
        mock_sb_user.return_value = sb_user
        mock_sb_admin.return_value = sb_admin

        person_q = MagicMock()
        # Truthy person_row but data is falsy
        person_q.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        sb_user.table.return_value = person_q

        user_service.delete_user("uid-y", "tok")

        sb_admin.auth.admin.delete_user.assert_called_once_with("uid-y")

    @patch("app.services.user_service.get_supabase")
    @patch("app.services.user_service.get_supabase_for_user")
    def test_should_propagate_error_when_supabase_admin_fails(
        self, mock_sb_user, mock_sb_admin
    ):
        sb_user = MagicMock()
        sb_admin = MagicMock()
        mock_sb_user.return_value = sb_user
        mock_sb_admin.return_value = sb_admin

        person_q = MagicMock()
        person_q.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        sb_user.table.return_value = person_q
        sb_admin.auth.admin.delete_user.side_effect = RuntimeError("auth API down")

        with pytest.raises(RuntimeError, match="auth API down"):
            user_service.delete_user("uid-x", "tok")
