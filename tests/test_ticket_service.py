"""Behavior-driven tests for ticket_service.

Tests cover:
- _resolve_guest_name: explicit name vs. lookup from person table
- _resolve_option_name: caching/passthrough vs. lookup
- _decrement_option_limit: capacity decrement with floor at 0
- ensure_participation_accepted: insert vs. update existing
- create_tickets_for_order: idempotency, multi-guest payloads, decrement
- create_tickets: free/RSVP path with guest_names update
- delete_tickets_for_event, delete_ticket_by_id
- get_tickets_for_person: shape, sort by ticket_number
- get_tickets_for_event: passthrough
- validate_ticket: not_found, already_used, success, signature failure
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services import ticket_service


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestResolveGuestName:
    def test_should_return_explicit_guest_name_when_provided(self):
        sb = MagicMock()
        result = ticket_service._resolve_guest_name(sb, "p-1", "Alice")
        assert result == "Alice"
        sb.table.assert_not_called()

    def test_should_lookup_full_name_from_person_when_not_provided(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"first_name": "Alice", "last_name": "Smith"}
        )
        result = ticket_service._resolve_guest_name(sb, "p-1", None)
        assert result == "Alice Smith"

    def test_should_default_to_gast_when_no_name_data_available(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={}
        )
        result = ticket_service._resolve_guest_name(sb, "p-1", None)
        assert result == "Gast"

    def test_should_handle_only_first_name(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"first_name": "Alice"}
        )
        result = ticket_service._resolve_guest_name(sb, "p-1", None)
        assert result == "Alice"

    def test_should_handle_none_data_field(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )
        result = ticket_service._resolve_guest_name(sb, "p-1", None)
        assert result == "Gast"


class TestResolveOptionName:
    def test_should_return_existing_option_name_unchanged(self):
        sb = MagicMock()
        result = ticket_service._resolve_option_name(sb, "opt-1", "VIP")
        assert result == "VIP"
        sb.table.assert_not_called()

    def test_should_return_none_when_option_id_is_missing(self):
        sb = MagicMock()
        result = ticket_service._resolve_option_name(sb, None, None)
        assert result is None
        sb.table.assert_not_called()

    def test_should_lookup_option_name_when_only_id_provided(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"name": "Early Bird"}
        )
        result = ticket_service._resolve_option_name(sb, "opt-1", None)
        assert result == "Early Bird"

    def test_should_return_none_when_lookup_returns_no_data(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )
        result = ticket_service._resolve_option_name(sb, "opt-1", None)
        assert result is None


class TestDecrementOptionLimit:
    def test_should_decrement_limit_by_amount(self):
        sb = MagicMock()
        # Mock the select chain returning current limit
        sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"quantity_limit": 10}
        )

        ticket_service._decrement_option_limit(sb, "opt-1", 3)

        # update() should have been called with new limit (10 - 3 = 7)
        update_call = sb.table.return_value.update.call_args
        assert update_call[0][0] == {"quantity_limit": 7}

    def test_should_floor_at_zero_when_amount_exceeds_limit(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"quantity_limit": 2}
        )

        ticket_service._decrement_option_limit(sb, "opt-1", 5)

        update_call = sb.table.return_value.update.call_args
        assert update_call[0][0] == {"quantity_limit": 0}

    def test_should_skip_when_amount_is_zero(self):
        sb = MagicMock()
        ticket_service._decrement_option_limit(sb, "opt-1", 0)
        sb.table.assert_not_called()

    def test_should_skip_when_option_id_is_empty(self):
        sb = MagicMock()
        ticket_service._decrement_option_limit(sb, "", 5)
        sb.table.assert_not_called()

    def test_should_skip_update_when_limit_is_none(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"quantity_limit": None}
        )

        ticket_service._decrement_option_limit(sb, "opt-1", 3)

        sb.table.return_value.update.assert_not_called()


# ---------------------------------------------------------------------------
# ensure_participation_accepted
# ---------------------------------------------------------------------------


class TestEnsureParticipationAccepted:
    def test_should_insert_new_participation_when_none_exists(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        ticket_service.ensure_participation_accepted(sb, "evt-1", "p-1")

        # insert should have been called
        insert_calls = [
            c for c in sb.table.return_value.insert.call_args_list
        ]
        assert len(insert_calls) >= 1

    def test_should_update_existing_participation_to_accepted(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"event_participation_id": "ep-1"}
        )

        ticket_service.ensure_participation_accepted(sb, "evt-1", "p-1")

        update_calls = sb.table.return_value.update.call_args_list
        assert update_calls
        assert update_calls[0][0][0] == {"status": "Accepted"}

    def test_should_handle_none_response_object(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = None

        # Should not crash; insert path is taken
        ticket_service.ensure_participation_accepted(sb, "evt-1", "p-1")


# ---------------------------------------------------------------------------
# create_tickets_for_order
# ---------------------------------------------------------------------------


def _stub_resolve_helpers(monkeypatch):
    monkeypatch.setattr(
        ticket_service, "_resolve_guest_name", lambda sb, pid, name: name or "Gast"
    )
    monkeypatch.setattr(
        ticket_service, "_resolve_option_name", lambda sb, oid, oname: oname
    )
    monkeypatch.setattr(
        ticket_service, "_decrement_option_limit", lambda sb, oid, amt: None
    )
    monkeypatch.setattr(
        ticket_service,
        "ensure_participation_accepted",
        lambda sb, eid, pid: None,
    )


class TestCreateTicketsForOrder:
    def test_should_return_existing_when_order_already_fully_processed(
        self, monkeypatch
    ):
        _stub_resolve_helpers(monkeypatch)
        sb = MagicMock()

        # Order already has 2 tickets, quantity asked is 2 → return existing
        existing_data = [{"ticket_id": "t-1"}, {"ticket_id": "t-2"}]

        def select_chain(*a, **kw):
            chain = MagicMock()
            chain.execute.return_value = MagicMock(data=existing_data, count=2)
            return chain

        sb.table.return_value.select.return_value.eq.return_value = select_chain()

        result = ticket_service.create_tickets_for_order(
            sb,
            ticket_order_id="o-1",
            event_id="evt-1",
            person_id="p-1",
            ticket_option_id="opt-1",
            quantity=2,
            guest_name="Alice",
        )

        # Idempotent: no new insert
        sb.table.return_value.insert.assert_not_called()

    def test_should_create_remaining_tickets_when_partially_processed(
        self, monkeypatch
    ):
        _stub_resolve_helpers(monkeypatch)

        sb = MagicMock()

        # First select() -> for ticket_order count → existing count = 1
        # Second select() -> for total existing (event+person) → count = 1 (concrete int!)
        first_select = MagicMock()
        first_select.eq.return_value.execute.return_value = MagicMock(
            data=[{"ticket_id": "t-1"}], count=1
        )
        second_select = MagicMock()
        second_select.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[], count=1
        )

        select_count = {"n": 0}

        def select_fn(*args, **kwargs):
            select_count["n"] += 1
            return first_select if select_count["n"] == 1 else second_select

        sb.table.return_value.select = select_fn

        insert_result = MagicMock()
        insert_result.execute.return_value = MagicMock(data=[{"ticket_id": "new-1"}])
        sb.table.return_value.insert.return_value = insert_result

        result = ticket_service.create_tickets_for_order(
            sb,
            ticket_order_id="o-1",
            event_id="evt-1",
            person_id="p-1",
            ticket_option_id="opt-1",
            quantity=2,
            guest_name="Alice",
        )

        # Should have called insert with 1 new payload
        sb.table.return_value.insert.assert_called_once()
        payloads = sb.table.return_value.insert.call_args[0][0]
        assert len(payloads) == 1
        assert payloads[0]["ticket_order_id"] == "o-1"

    def test_should_create_all_tickets_when_none_exist_yet(self, monkeypatch):
        _stub_resolve_helpers(monkeypatch)

        sb = MagicMock()

        # Setup the chain returns for both select() calls
        first_select = MagicMock()
        first_select.eq.return_value.execute.return_value = MagicMock(data=[], count=0)
        second_select = MagicMock()
        second_select.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[], count=0
        )

        select_count = {"n": 0}

        def select_fn(*args, **kwargs):
            select_count["n"] += 1
            return first_select if select_count["n"] == 1 else second_select

        sb.table.return_value.select = select_fn

        insert_result = MagicMock()
        insert_result.execute.return_value = MagicMock(
            data=[{"ticket_id": "new-1"}, {"ticket_id": "new-2"}]
        )
        sb.table.return_value.insert.return_value = insert_result

        result = ticket_service.create_tickets_for_order(
            sb,
            ticket_order_id="o-1",
            event_id="evt-1",
            person_id="p-1",
            ticket_option_id=None,
            quantity=2,
            guest_name="Alice",
        )

        sb.table.return_value.insert.assert_called_once()
        payloads = sb.table.return_value.insert.call_args[0][0]
        assert len(payloads) == 2
        # No ticket_option_id set when None
        assert "ticket_option_id" not in payloads[0]

    def test_should_use_provided_guest_names_for_each_ticket(self, monkeypatch):
        _stub_resolve_helpers(monkeypatch)

        sb = MagicMock()

        first_select = MagicMock()
        first_select.eq.return_value.execute.return_value = MagicMock(data=[], count=0)
        second_select = MagicMock()
        second_select.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[], count=0
        )

        select_count = {"n": 0}

        def select_fn(*args, **kwargs):
            select_count["n"] += 1
            return first_select if select_count["n"] == 1 else second_select

        sb.table.return_value.select = select_fn
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[]
        )

        ticket_service.create_tickets_for_order(
            sb,
            ticket_order_id="o-1",
            event_id="evt-1",
            person_id="p-1",
            ticket_option_id=None,
            quantity=2,
            guest_name="Alice",
            guest_names=["Bob", "Carol"],
        )

        payloads = sb.table.return_value.insert.call_args[0][0]
        assert payloads[0]["guest_name"] == "Bob"
        assert payloads[1]["guest_name"] == "Carol"


# ---------------------------------------------------------------------------
# create_tickets (free path)
# ---------------------------------------------------------------------------


class TestCreateTickets:
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_create_tickets_for_free_event(self, mock_get_sb, monkeypatch):
        _stub_resolve_helpers(monkeypatch)
        sb = MagicMock()
        mock_get_sb.return_value = sb

        select_chain = MagicMock()
        select_chain.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[], count=0
        )
        sb.table.return_value.select.return_value = select_chain

        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"ticket_id": "new"}]
        )

        result = ticket_service.create_tickets(
            "evt-1", "p-1", "tok", quantity=1, guest_name="Alice"
        )

        sb.table.return_value.insert.assert_called_once()

    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_return_empty_when_already_at_quantity(
        self, mock_get_sb, monkeypatch
    ):
        _stub_resolve_helpers(monkeypatch)
        sb = MagicMock()
        mock_get_sb.return_value = sb

        select_chain = MagicMock()
        select_chain.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"ticket_id": "t-1"}], count=1
        )
        sb.table.return_value.select.return_value = select_chain

        result = ticket_service.create_tickets(
            "evt-1", "p-1", "tok", quantity=1, guest_name="Alice"
        )

        assert result == []
        sb.table.return_value.insert.assert_not_called()

    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_update_guest_names_when_guest_names_provided_with_existing(
        self, mock_get_sb, monkeypatch
    ):
        _stub_resolve_helpers(monkeypatch)
        sb = MagicMock()
        mock_get_sb.return_value = sb

        select_chain = MagicMock()
        select_chain.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"ticket_id": "t-1"}, {"ticket_id": "t-2"}], count=2
        )
        sb.table.return_value.select.return_value = select_chain

        result = ticket_service.create_tickets(
            "evt-1",
            "p-1",
            "tok",
            quantity=2,
            guest_name="Alice",
            guest_names=["Bob", "Carol"],
        )

        # 2 update calls for renaming existing tickets
        update_calls = [
            c
            for c in sb.table.return_value.update.call_args_list
            if "guest_name" in c[0][0]
        ]
        assert len(update_calls) == 2

    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_propagate_supabase_failure(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.side_effect = RuntimeError("DB down")

        with pytest.raises(RuntimeError, match="DB down"):
            ticket_service.create_tickets("evt-1", "p-1", "tok")


# ---------------------------------------------------------------------------
# delete_tickets_for_event / delete_ticket_by_id
# ---------------------------------------------------------------------------


class TestDeleteTicketsForEvent:
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_delete_only_free_tickets(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        ticket_service.delete_tickets_for_event("evt-1", "p-1", "tok")

        # The is_("ticket_order_id", "null") call is what restricts to free tickets
        delete_chain = sb.table.return_value.delete.return_value
        delete_chain.eq.return_value.eq.return_value.is_.assert_called_once_with(
            "ticket_order_id", "null"
        )

    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_propagate_failure(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError):
            ticket_service.delete_tickets_for_event("evt-1", "p-1", "tok")


class TestDeleteTicketById:
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_delete_ticket_by_id(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        ticket_service.delete_ticket_by_id("t-1", "tok")

        sb.table.return_value.delete.return_value.eq.assert_called_once_with(
            "ticket_id", "t-1"
        )

    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_propagate_failure(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.side_effect = RuntimeError("err")

        with pytest.raises(RuntimeError):
            ticket_service.delete_ticket_by_id("t-1", "tok")


# ---------------------------------------------------------------------------
# get_tickets_for_person
# ---------------------------------------------------------------------------


class TestGetTicketsForPerson:
    @patch("app.services.ticket_service.verify_ticket_token")
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_return_empty_when_person_has_no_tickets(
        self, mock_get_sb, mock_verify
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = ticket_service.get_tickets_for_person("p-1", "tok")

        assert result == {"tickets": [], "total": 0}

    @patch("app.services.ticket_service.verify_ticket_token")
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_flatten_event_and_option_details(self, mock_get_sb, mock_verify):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        mock_verify.return_value = {"nr": 1}

        sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "ticket_id": "t-1",
                    "qr_token": "tok-1",
                    "status": "active",
                    "created_at": "2026-06-01T10:00:00Z",
                    "used_at": None,
                    "guest_name": "Alice",
                    "event": {
                        "event_id": "evt-1",
                        "title": "Concert",
                        "starts_at": "2026-09-01T18:00:00Z",
                        "location": {"city": "Berlin"},
                    },
                    "ticket_option": {
                        "ticket_option_id": "opt-1",
                        "name": "VIP",
                        "price": 25.5,
                    },
                }
            ]
        )

        result = ticket_service.get_tickets_for_person("p-1", "tok")

        assert result["total"] == 1
        t = result["tickets"][0]
        assert t["event_title"] == "Concert"
        assert t["ticket_option_name"] == "VIP"
        assert t["price"] == 25.5
        assert t["city"] == "Berlin"
        assert t["currency"] == "EUR"
        assert t["ticket_number"] == 1

    @patch("app.services.ticket_service.verify_ticket_token")
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_sort_tickets_by_ticket_number(self, mock_get_sb, mock_verify):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        # Return tickets in non-sorted order; verify_ticket_token returns numbers
        mock_verify.side_effect = [{"nr": 3}, {"nr": 1}, {"nr": 2}]

        sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "ticket_id": f"t-{i}",
                    "qr_token": f"q-{i}",
                    "event": {"event_id": "evt"},
                    "ticket_option": {},
                }
                for i in range(3)
            ]
        )

        result = ticket_service.get_tickets_for_person("p-1", "tok")

        numbers = [t["ticket_number"] for t in result["tickets"]]
        assert numbers == [1, 2, 3]

    @patch("app.services.ticket_service.verify_ticket_token")
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_default_option_name_when_no_option(self, mock_get_sb, mock_verify):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        mock_verify.return_value = {"nr": 1}

        sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "ticket_id": "t-1",
                    "qr_token": "q-1",
                    "event": {"event_id": "evt"},
                    "ticket_option": None,
                }
            ]
        )

        result = ticket_service.get_tickets_for_person("p-1", "tok")
        assert result["tickets"][0]["ticket_option_name"] == "Standard"
        assert result["tickets"][0]["price"] == 0.0

    @patch("app.services.ticket_service.verify_ticket_token")
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_handle_invalid_qr_token_gracefully(self, mock_get_sb, mock_verify):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        mock_verify.return_value = None  # signature failed

        sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "ticket_id": "t-1",
                    "qr_token": "bogus",
                    "event": {"event_id": "evt"},
                    "ticket_option": {},
                }
            ]
        )

        result = ticket_service.get_tickets_for_person("p-1", "tok")
        assert result["tickets"][0]["ticket_number"] is None


# ---------------------------------------------------------------------------
# get_tickets_for_event
# ---------------------------------------------------------------------------


class TestGetTicketsForEvent:
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_return_tickets_for_event_and_person(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"ticket_id": "t-1", "qr_token": "q", "guest_name": "A", "status": "active"}]
        )

        result = ticket_service.get_tickets_for_event("evt-1", "p-1", "tok")
        assert len(result) == 1

    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_return_empty_list_when_no_rows(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = ticket_service.get_tickets_for_event("evt-1", "p-1", "tok")
        assert result == []


# ---------------------------------------------------------------------------
# validate_ticket
# ---------------------------------------------------------------------------


class TestValidateTicket:
    @patch("app.services.ticket_service.verify_ticket_token")
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_return_not_found_when_signature_is_invalid(
        self, mock_get_sb, mock_verify
    ):
        mock_verify.return_value = None

        result = ticket_service.validate_ticket("evt-1", "fake-token", "tok")

        assert result == {"valid": False, "reason": "not_found"}

    @patch("app.services.ticket_service.verify_ticket_token")
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_return_not_found_when_ticket_row_missing(
        self, mock_get_sb, mock_verify
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        mock_verify.return_value = {"name": "A", "nr": 1, "opt": "Std"}

        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = None

        result = ticket_service.validate_ticket("evt-1", "good-token", "tok")

        assert result == {"valid": False, "reason": "not_found"}

    @patch("app.services.ticket_service.verify_ticket_token")
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_return_already_used_when_ticket_status_is_used(
        self, mock_get_sb, mock_verify
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        mock_verify.return_value = {"name": "A", "nr": 1, "opt": "Std"}

        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "ticket_id": "t-1",
                "status": "used",
                "used_at": "2026-06-01T10:00:00Z",
            }
        )

        result = ticket_service.validate_ticket("evt-1", "good-token", "tok")

        assert result["valid"] is False
        assert result["reason"] == "already_used"
        assert result["used_at"] == "2026-06-01T10:00:00Z"
        assert result["guest_name"] == "A"

    @patch("app.services.ticket_service.verify_ticket_token")
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_mark_ticket_as_used_on_success(self, mock_get_sb, mock_verify):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        mock_verify.return_value = {"name": "A", "nr": 5, "opt": "VIP"}

        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"ticket_id": "t-1", "status": "active", "used_at": None}
        )
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"ticket_id": "t-1"}]
        )

        result = ticket_service.validate_ticket("evt-1", "good-token", "tok")

        assert result["valid"] is True
        assert result["ticket_number"] == 5
        assert result["option_name"] == "VIP"
        assert "used_at" in result

    @patch("app.services.ticket_service.verify_ticket_token")
    @patch("app.services.ticket_service.get_supabase_for_user")
    def test_should_raise_permission_error_when_update_returns_no_data(
        self, mock_get_sb, mock_verify
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        mock_verify.return_value = {"name": "A", "nr": 1, "opt": None}

        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"ticket_id": "t-1", "status": "active", "used_at": None}
        )
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=None
        )

        with pytest.raises(PermissionError):
            ticket_service.validate_ticket("evt-1", "good-token", "tok")
