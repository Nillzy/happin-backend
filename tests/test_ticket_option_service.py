"""Behavior-driven tests for ticket_option_service.

Tests cover:
- get_ticket_options: ordered fetch
- sync_ticket_options: insert/update/delete, Stripe-precondition, event.is_free sync
- _sync_event_is_free: updates the event flag based on pricing
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services import ticket_option_service


# ---------------------------------------------------------------------------
# get_ticket_options
# ---------------------------------------------------------------------------


class TestGetTicketOptions:
    @patch("app.services.ticket_option_service.get_supabase")
    def test_should_return_options_ordered_by_sort_order(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {"ticket_option_id": "o-1", "name": "Standard", "sort_order": 0},
                {"ticket_option_id": "o-2", "name": "VIP", "sort_order": 1},
            ]
        )

        result = ticket_option_service.get_ticket_options("evt-1")

        assert len(result) == 2
        sb.table.return_value.select.return_value.eq.return_value.order.assert_called_once_with(
            "sort_order"
        )

    @patch("app.services.ticket_option_service.get_supabase")
    def test_should_return_empty_list_when_event_has_no_options(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        assert ticket_option_service.get_ticket_options("evt-1") == []

    @patch("app.services.ticket_option_service.get_supabase")
    def test_should_propagate_supabase_error(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError):
            ticket_option_service.get_ticket_options("evt-1")


# ---------------------------------------------------------------------------
# _sync_event_is_free
# ---------------------------------------------------------------------------


class TestSyncEventIsFree:
    def test_should_set_is_free_false_when_any_option_has_price(self):
        sb = MagicMock()

        ticket_option_service._sync_event_is_free(
            sb, "evt-1", [{"price": 0}, {"price": 10}]
        )

        update_payload = sb.table.return_value.update.call_args[0][0]
        assert update_payload == {"is_free": False}

    def test_should_set_is_free_true_when_all_options_are_zero(self):
        sb = MagicMock()

        ticket_option_service._sync_event_is_free(
            sb, "evt-1", [{"price": 0}, {"price": 0}]
        )

        update_payload = sb.table.return_value.update.call_args[0][0]
        assert update_payload == {"is_free": True}

    def test_should_set_is_free_true_when_no_options(self):
        sb = MagicMock()
        ticket_option_service._sync_event_is_free(sb, "evt-1", [])
        update_payload = sb.table.return_value.update.call_args[0][0]
        assert update_payload == {"is_free": True}

    def test_should_treat_none_price_as_free(self):
        sb = MagicMock()
        ticket_option_service._sync_event_is_free(
            sb, "evt-1", [{"price": None}]
        )
        update_payload = sb.table.return_value.update.call_args[0][0]
        assert update_payload == {"is_free": True}

    def test_should_filter_by_event_id(self):
        sb = MagicMock()
        ticket_option_service._sync_event_is_free(sb, "evt-1", [{"price": 5}])
        eq_call = sb.table.return_value.update.return_value.eq.call_args
        assert eq_call[0] == ("event_id", "evt-1")


# ---------------------------------------------------------------------------
# sync_ticket_options
# ---------------------------------------------------------------------------


class TestSyncTicketOptions:
    @patch("app.services.ticket_option_service.payment_service.require_stripe_for_paid_public_tickets")
    @patch("app.services.ticket_option_service.get_ticket_options")
    @patch("app.services.ticket_option_service.get_supabase_for_user")
    def test_should_insert_new_option_when_no_id_provided(
        self, mock_get_sb, mock_get_options, mock_require_stripe
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_get_options.return_value = [{"ticket_option_id": "new", "price": 0}]

        ticket_option_service.sync_ticket_options(
            "evt-1",
            [{"name": "Standard", "price": 0, "sort_order": 0}],
            "tok",
        )

        sb.table.return_value.insert.assert_called_once()
        insert_payload = sb.table.return_value.insert.call_args[0][0]
        assert insert_payload["name"] == "Standard"
        assert insert_payload["price"] == 0
        # Stripe precondition checked
        mock_require_stripe.assert_called_once()

    @patch("app.services.ticket_option_service.payment_service.require_stripe_for_paid_public_tickets")
    @patch("app.services.ticket_option_service.get_ticket_options")
    @patch("app.services.ticket_option_service.get_supabase_for_user")
    def test_should_update_existing_option_when_id_matches(
        self, mock_get_sb, mock_get_options, mock_require_stripe
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"ticket_option_id": "o-1"}]
        )
        mock_get_options.return_value = []

        ticket_option_service.sync_ticket_options(
            "evt-1",
            [
                {
                    "ticket_option_id": "o-1",
                    "name": "Updated",
                    "price": 20,
                }
            ],
            "tok",
        )

        update_calls = sb.table.return_value.update.call_args_list
        assert update_calls
        update_payload = update_calls[0][0][0]
        assert update_payload["name"] == "Updated"
        assert update_payload["price"] == 20

    @patch("app.services.ticket_option_service.payment_service.require_stripe_for_paid_public_tickets")
    @patch("app.services.ticket_option_service.get_ticket_options")
    @patch("app.services.ticket_option_service.get_supabase_for_user")
    def test_should_delete_options_not_in_incoming(
        self, mock_get_sb, mock_get_options, mock_require_stripe
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"ticket_option_id": "o-1"}, {"ticket_option_id": "o-2"}]
        )
        mock_get_options.return_value = []

        ticket_option_service.sync_ticket_options(
            "evt-1",
            [{"ticket_option_id": "o-1", "name": "Keep", "price": 0}],
            "tok",
        )

        delete_chain = sb.table.return_value.delete.return_value
        delete_chain.in_.assert_called_once()
        deleted_ids = delete_chain.in_.call_args[0][1]
        assert deleted_ids == ["o-2"]

    @patch("app.services.ticket_option_service.payment_service.require_stripe_for_paid_public_tickets")
    @patch("app.services.ticket_option_service.get_ticket_options")
    @patch("app.services.ticket_option_service.get_supabase_for_user")
    def test_should_not_delete_when_no_orphans_exist(
        self, mock_get_sb, mock_get_options, mock_require_stripe
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_get_options.return_value = []

        ticket_option_service.sync_ticket_options("evt-1", [], "tok")

        sb.table.return_value.delete.assert_not_called()

    @patch("app.services.ticket_option_service.payment_service.require_stripe_for_paid_public_tickets")
    @patch("app.services.ticket_option_service.get_ticket_options")
    @patch("app.services.ticket_option_service.get_supabase_for_user")
    def test_should_treat_unknown_id_as_insert(
        self, mock_get_sb, mock_get_options, mock_require_stripe
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_get_options.return_value = []

        ticket_option_service.sync_ticket_options(
            "evt-1",
            [
                {
                    "ticket_option_id": "stale",
                    "name": "Will insert",
                    "price": 5,
                }
            ],
            "tok",
        )

        sb.table.return_value.insert.assert_called_once()
        # No ticket_option UPDATE call — only the trailing event.is_free update is allowed.
        ticket_option_updates = [
            c
            for c in sb.table.return_value.update.call_args_list
            if "is_free" not in c[0][0]
        ]
        assert ticket_option_updates == []

    @patch("app.services.ticket_option_service.payment_service.require_stripe_for_paid_public_tickets")
    @patch("app.services.ticket_option_service.get_ticket_options")
    @patch("app.services.ticket_option_service.get_supabase_for_user")
    def test_should_sync_event_is_free_to_false_when_paid_options_exist(
        self, mock_get_sb, mock_get_options, mock_require_stripe
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        # Result has one paid option
        mock_get_options.return_value = [{"price": 10}]

        ticket_option_service.sync_ticket_options(
            "evt-1", [{"name": "Paid", "price": 10}], "tok"
        )

        # The very last call on the 'event' table must be update({"is_free": False})
        event_updates = [
            c
            for c in sb.table.return_value.update.call_args_list
            if c[0][0] == {"is_free": False}
        ]
        assert event_updates

    @patch("app.services.ticket_option_service.payment_service.require_stripe_for_paid_public_tickets")
    @patch("app.services.ticket_option_service.get_ticket_options")
    @patch("app.services.ticket_option_service.get_supabase_for_user")
    def test_should_sync_event_is_free_to_true_when_all_options_free(
        self, mock_get_sb, mock_get_options, mock_require_stripe
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_get_options.return_value = [{"price": 0}]

        ticket_option_service.sync_ticket_options(
            "evt-1", [{"name": "Free", "price": 0}], "tok"
        )

        event_updates = [
            c
            for c in sb.table.return_value.update.call_args_list
            if c[0][0] == {"is_free": True}
        ]
        assert event_updates

    @patch("app.services.ticket_option_service.payment_service.require_stripe_for_paid_public_tickets")
    @patch("app.services.ticket_option_service.get_ticket_options")
    @patch("app.services.ticket_option_service.get_supabase_for_user")
    def test_should_raise_when_stripe_precondition_fails(
        self, mock_get_sb, mock_get_options, mock_require_stripe
    ):
        from fastapi import HTTPException

        mock_require_stripe.side_effect = HTTPException(
            status_code=400, detail="stripe_required"
        )

        with pytest.raises(HTTPException):
            ticket_option_service.sync_ticket_options(
                "evt-1", [{"name": "Paid", "price": 10}], "tok"
            )

    @patch("app.services.ticket_option_service.payment_service.require_stripe_for_paid_public_tickets")
    @patch("app.services.ticket_option_service.get_ticket_options")
    @patch("app.services.ticket_option_service.get_supabase_for_user")
    def test_should_return_canonical_list_from_get_ticket_options(
        self, mock_get_sb, mock_get_options, mock_require_stripe
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        canonical = [{"ticket_option_id": "o-new", "name": "S", "price": 0}]
        mock_get_options.return_value = canonical

        result = ticket_option_service.sync_ticket_options("evt-1", [], "tok")

        assert result == canonical

    @patch("app.services.ticket_option_service.payment_service.require_stripe_for_paid_public_tickets")
    @patch("app.services.ticket_option_service.get_ticket_options")
    @patch("app.services.ticket_option_service.get_supabase_for_user")
    def test_should_default_price_to_zero_when_not_provided(
        self, mock_get_sb, mock_get_options, mock_require_stripe
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_get_options.return_value = []

        ticket_option_service.sync_ticket_options(
            "evt-1", [{"name": "X"}], "tok"
        )

        insert_payload = sb.table.return_value.insert.call_args[0][0]
        assert insert_payload["price"] == 0.0
        assert insert_payload["sort_order"] == 0
        assert insert_payload["quantity_limit"] is None
