"""Behavior-driven tests for custom_field_service.

Tests cover:
- get_custom_fields: ordered fetch by sort_order
- sync_custom_fields: insert new, update existing, delete missing (full sync semantics)
- submit_responses: upsert per custom_field_id
- get_responses_for_ticket: select + eq passthrough
- get_my_responses: per-ticket grouping
- get_all_responses_for_event: inner join semantics
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services import custom_field_service


# ---------------------------------------------------------------------------
# get_custom_fields
# ---------------------------------------------------------------------------


class TestGetCustomFields:
    @patch("app.services.custom_field_service.get_supabase")
    def test_should_return_fields_ordered_by_sort_order(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {"custom_field_id": "f-1", "label": "Name", "sort_order": 0},
                {"custom_field_id": "f-2", "label": "Email", "sort_order": 1},
            ]
        )

        result = custom_field_service.get_custom_fields("evt-1")

        assert len(result) == 2
        # Verify order column was passed
        sb.table.return_value.select.return_value.eq.return_value.order.assert_called_once_with(
            "sort_order"
        )

    @patch("app.services.custom_field_service.get_supabase")
    def test_should_return_empty_list_when_event_has_no_fields(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = custom_field_service.get_custom_fields("evt-1")
        assert result == []

    @patch("app.services.custom_field_service.get_supabase")
    def test_should_propagate_supabase_error(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError):
            custom_field_service.get_custom_fields("evt-1")


# ---------------------------------------------------------------------------
# sync_custom_fields
# ---------------------------------------------------------------------------


class TestSyncCustomFields:
    @patch("app.services.event_service._ensure_event_active")
    @patch("app.services.custom_field_service.get_supabase")
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_insert_new_field_when_no_id_provided(
        self, mock_get_sb_user, mock_get_sb_admin, mock_ensure_active
    ):
        sb_user = MagicMock()
        mock_get_sb_user.return_value = sb_user
        # Admin client used by get_custom_fields at the end
        sb_admin = MagicMock()
        mock_get_sb_admin.return_value = sb_admin

        # No existing fields
        sb_user.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        # Final get_custom_fields returns the new field
        sb_admin.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"custom_field_id": "new-1", "label": "Name"}]
        )

        result = custom_field_service.sync_custom_fields(
            "evt-1",
            [{"label": "Name", "field_type": "text"}],
            "tok",
        )

        sb_user.table.return_value.insert.assert_called_once()
        insert_payload = sb_user.table.return_value.insert.call_args[0][0]
        assert insert_payload["label"] == "Name"
        assert insert_payload["field_type"] == "text"
        assert insert_payload["is_required"] is False
        assert insert_payload["sort_order"] == 0
        mock_ensure_active.assert_called_once_with("evt-1", "tok")

    @patch("app.services.event_service._ensure_event_active")
    @patch("app.services.custom_field_service.get_supabase")
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_update_existing_field_when_id_matches(
        self, mock_get_sb_user, mock_get_sb_admin, mock_ensure_active
    ):
        sb_user = MagicMock()
        sb_admin = MagicMock()
        mock_get_sb_user.return_value = sb_user
        mock_get_sb_admin.return_value = sb_admin

        # Existing field with id f-1
        sb_user.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"custom_field_id": "f-1"}]
        )
        sb_admin.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        custom_field_service.sync_custom_fields(
            "evt-1",
            [
                {
                    "custom_field_id": "f-1",
                    "label": "Updated",
                    "field_type": "text",
                    "is_required": True,
                }
            ],
            "tok",
        )

        # update called with f-1
        update_calls = sb_user.table.return_value.update.call_args_list
        assert update_calls
        update_payload = update_calls[0][0][0]
        assert update_payload["label"] == "Updated"
        assert update_payload["is_required"] is True

    @patch("app.services.event_service._ensure_event_active")
    @patch("app.services.custom_field_service.get_supabase")
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_delete_fields_not_present_in_incoming(
        self, mock_get_sb_user, mock_get_sb_admin, mock_ensure_active
    ):
        sb_user = MagicMock()
        sb_admin = MagicMock()
        mock_get_sb_user.return_value = sb_user
        mock_get_sb_admin.return_value = sb_admin

        # Existing fields: f-1, f-2. Incoming only has f-1 → f-2 deleted.
        sb_user.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"custom_field_id": "f-1"}, {"custom_field_id": "f-2"}]
        )
        sb_admin.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        custom_field_service.sync_custom_fields(
            "evt-1",
            [
                {"custom_field_id": "f-1", "label": "Keep", "field_type": "text"},
            ],
            "tok",
        )

        # delete().in_("custom_field_id", ["f-2"]) called
        delete_chain = sb_user.table.return_value.delete.return_value
        delete_chain.in_.assert_called_once()
        deleted_ids = delete_chain.in_.call_args[0][1]
        assert deleted_ids == ["f-2"]

    @patch("app.services.event_service._ensure_event_active")
    @patch("app.services.custom_field_service.get_supabase")
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_not_call_delete_when_no_fields_to_remove(
        self, mock_get_sb_user, mock_get_sb_admin, mock_ensure_active
    ):
        sb_user = MagicMock()
        sb_admin = MagicMock()
        mock_get_sb_user.return_value = sb_user
        mock_get_sb_admin.return_value = sb_admin

        sb_user.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        sb_admin.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        custom_field_service.sync_custom_fields("evt-1", [], "tok")

        sb_user.table.return_value.delete.assert_not_called()

    @patch("app.services.event_service._ensure_event_active")
    @patch("app.services.custom_field_service.get_supabase")
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_treat_unknown_id_as_insert(
        self, mock_get_sb_user, mock_get_sb_admin, mock_ensure_active
    ):
        """If a field has a custom_field_id but it isn't in existing_ids, treat as insert."""
        sb_user = MagicMock()
        sb_admin = MagicMock()
        mock_get_sb_user.return_value = sb_user
        mock_get_sb_admin.return_value = sb_admin

        sb_user.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        sb_admin.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        custom_field_service.sync_custom_fields(
            "evt-1",
            [
                {
                    "custom_field_id": "stale-id",
                    "label": "Should be inserted",
                    "field_type": "text",
                }
            ],
            "tok",
        )

        sb_user.table.return_value.insert.assert_called_once()
        sb_user.table.return_value.update.assert_not_called()

    @patch("app.services.event_service._ensure_event_active")
    @patch("app.services.custom_field_service.get_supabase")
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_raise_when_event_is_inactive(
        self, mock_get_sb_user, mock_get_sb_admin, mock_ensure_active
    ):
        from fastapi import HTTPException

        mock_ensure_active.side_effect = HTTPException(
            status_code=400, detail="event_cancelled"
        )

        with pytest.raises(HTTPException):
            custom_field_service.sync_custom_fields("evt-1", [], "tok")

    @patch("app.services.event_service._ensure_event_active")
    @patch("app.services.custom_field_service.get_supabase")
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_propagate_options_and_required_flag(
        self, mock_get_sb_user, mock_get_sb_admin, mock_ensure_active
    ):
        sb_user = MagicMock()
        sb_admin = MagicMock()
        mock_get_sb_user.return_value = sb_user
        mock_get_sb_admin.return_value = sb_admin

        sb_user.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        sb_admin.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        custom_field_service.sync_custom_fields(
            "evt-1",
            [
                {
                    "label": "Diet",
                    "field_type": "select",
                    "is_required": True,
                    "options": ["Vegan", "Standard"],
                    "sort_order": 3,
                }
            ],
            "tok",
        )

        payload = sb_user.table.return_value.insert.call_args[0][0]
        assert payload["options"] == ["Vegan", "Standard"]
        assert payload["is_required"] is True
        assert payload["sort_order"] == 3


# ---------------------------------------------------------------------------
# submit_responses
# ---------------------------------------------------------------------------


class TestSubmitResponses:
    @patch("app.services.custom_field_service.get_responses_for_ticket")
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_upsert_each_response_with_conflict_key(
        self, mock_get_sb, mock_get_responses
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        mock_get_responses.return_value = []

        custom_field_service.submit_responses(
            "t-1",
            [
                {"custom_field_id": "f-1", "value": "Alice"},
                {"custom_field_id": "f-2", "value": "Vegan"},
            ],
            "tok",
        )

        upsert_calls = sb.table.return_value.upsert.call_args_list
        assert len(upsert_calls) == 2
        # First call has the right row + on_conflict key
        first_payload = upsert_calls[0][0][0]
        assert first_payload["ticket_id"] == "t-1"
        assert first_payload["custom_field_id"] == "f-1"
        assert upsert_calls[0][1]["on_conflict"] == "ticket_id,custom_field_id"

    @patch("app.services.custom_field_service.get_responses_for_ticket")
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_return_current_responses_after_upsert(
        self, mock_get_sb, mock_get_responses
    ):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        mock_get_responses.return_value = [{"custom_field_id": "f-1", "value": "Alice"}]

        result = custom_field_service.submit_responses(
            "t-1", [{"custom_field_id": "f-1", "value": "Alice"}], "tok"
        )

        assert result == [{"custom_field_id": "f-1", "value": "Alice"}]
        mock_get_responses.assert_called_once_with("t-1", "tok")

    @patch("app.services.custom_field_service.get_responses_for_ticket")
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_handle_empty_responses(self, mock_get_sb, mock_get_responses):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        mock_get_responses.return_value = []

        result = custom_field_service.submit_responses("t-1", [], "tok")

        sb.table.return_value.upsert.assert_not_called()
        assert result == []

    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_propagate_error_from_upsert(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.upsert.side_effect = RuntimeError("constraint failed")

        with pytest.raises(RuntimeError):
            custom_field_service.submit_responses(
                "t-1", [{"custom_field_id": "f-1", "value": "x"}], "tok"
            )


# ---------------------------------------------------------------------------
# get_responses_for_ticket
# ---------------------------------------------------------------------------


class TestGetResponsesForTicket:
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_return_responses_for_given_ticket(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"custom_field_id": "f-1", "value": "Alice"}]
        )

        result = custom_field_service.get_responses_for_ticket("t-1", "tok")

        assert result == [{"custom_field_id": "f-1", "value": "Alice"}]

    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_return_empty_when_no_responses_exist(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        assert custom_field_service.get_responses_for_ticket("t-1", "tok") == []

    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_propagate_supabase_error(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.side_effect = RuntimeError("oops")

        with pytest.raises(RuntimeError):
            custom_field_service.get_responses_for_ticket("t-1", "tok")


# ---------------------------------------------------------------------------
# get_my_responses
# ---------------------------------------------------------------------------


class TestGetMyResponses:
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_group_responses_per_ticket(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        # ticket lookup -> 2 tickets
        ticket_q = MagicMock()
        ticket_q.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"ticket_id": "t-1"}, {"ticket_id": "t-2"}]
        )

        # responses per ticket
        responses_q = MagicMock()
        execute_results = [
            MagicMock(data=[{"custom_field_id": "f-1", "value": "Alice"}]),
            MagicMock(data=[{"custom_field_id": "f-1", "value": "Bob"}]),
        ]
        responses_q.select.return_value.eq.return_value.execute.side_effect = execute_results

        def table(name):
            return ticket_q if name == "ticket" else responses_q

        sb.table.side_effect = table

        result = custom_field_service.get_my_responses("evt-1", "p-1", "tok")

        assert len(result) == 2
        assert result[0]["ticket_id"] == "t-1"
        assert result[0]["responses"] == [{"custom_field_id": "f-1", "value": "Alice"}]
        assert result[1]["ticket_id"] == "t-2"

    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_return_empty_when_user_has_no_tickets(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        ticket_q = MagicMock()
        ticket_q.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        sb.table.return_value = ticket_q

        result = custom_field_service.get_my_responses("evt-1", "p-1", "tok")
        assert result == []

    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_handle_none_data_in_tickets(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        ticket_q = MagicMock()
        ticket_q.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=None
        )
        sb.table.return_value = ticket_q

        result = custom_field_service.get_my_responses("evt-1", "p-1", "tok")
        assert result == []

    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_handle_none_data_in_responses(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb

        ticket_q = MagicMock()
        ticket_q.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"ticket_id": "t-1"}]
        )
        responses_q = MagicMock()
        responses_q.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=None
        )

        sb.table.side_effect = lambda name: (
            ticket_q if name == "ticket" else responses_q
        )

        result = custom_field_service.get_my_responses("evt-1", "p-1", "tok")
        assert result == [{"ticket_id": "t-1", "responses": []}]


# ---------------------------------------------------------------------------
# get_all_responses_for_event
# ---------------------------------------------------------------------------


class TestGetAllResponsesForEvent:
    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_return_responses_with_inner_join_filter(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "ticket_id": "t-1",
                    "custom_field_id": "f-1",
                    "value": "Alice",
                    "ticket": {"event_id": "evt-1"},
                }
            ]
        )

        result = custom_field_service.get_all_responses_for_event("evt-1", "tok")

        assert len(result) == 1
        # Verify the filter uses the nested column
        eq_call = sb.table.return_value.select.return_value.eq.call_args
        assert eq_call[0][0] == "ticket.event_id"

    @patch("app.services.custom_field_service.get_supabase_for_user")
    def test_should_return_empty_when_no_responses(self, mock_get_sb):
        sb = MagicMock()
        mock_get_sb.return_value = sb
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        assert custom_field_service.get_all_responses_for_event("evt-1", "tok") == []
