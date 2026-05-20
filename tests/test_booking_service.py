"""Tests for shared booking validation."""

from unittest.mock import MagicMock, patch

import pytest

from app.services import booking_service


def _mock_supabase_for_validate(*, event_id: str, max_capacity: int | None, max_per_person: int):
    mock_sb = MagicMock()

    def table_side_effect(name):
        t = MagicMock()
        if name == "event":
            t.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                data={"max_capacity": max_capacity, "max_tickets_per_person": max_per_person}
            )
        elif name == "ticket_option":
            t.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "ticket_option_id": "opt-1",
                    "event_id": event_id,
                    "name": "Standard",
                    "price": "10.00",
                    "quantity_limit": 50,
                }
            )
        elif name == "ticket":
            t.select.return_value.eq.return_value.execute.return_value = MagicMock(count=0)
            t.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(count=0)
        elif name == "ticket_order":
            t.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            t.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            t.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )
            t.select.return_value.eq.return_value.eq.return_value.not_.return_value.is_.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )
        return t

    mock_sb.table.side_effect = table_side_effect
    return mock_sb


class TestValidateBooking:
    def test_wrong_event_raises(self):
        mock_sb = _mock_supabase_for_validate(event_id="other", max_capacity=100, max_per_person=2)
        with pytest.raises(ValueError, match="ticket_option_wrong_event"):
            booking_service.validate_booking(
                mock_sb,
                event_id="event-a",
                person_id="p1",
                quantity=1,
                ticket_option_id="opt-1",
                is_checkout=True,
            )

    def test_max_tickets_exceeded_raises(self):
        mock_sb = MagicMock()

        def table_side_effect(name):
            t = MagicMock()
            if name == "event":
                t.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                    data={"max_capacity": 100, "max_tickets_per_person": 2}
                )
            elif name == "ticket_option":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={
                        "ticket_option_id": "opt-1",
                        "event_id": "event-a",
                        "name": "VIP",
                        "price": "10.00",
                        "quantity_limit": 50,
                    }
                )
            elif name == "ticket":
                count_resp = MagicMock(count=2)
                t.select.return_value.eq.return_value.execute.return_value = count_resp
                t.select.return_value.eq.return_value.eq.return_value.execute.return_value = count_resp
            elif name == "ticket_order":
                t.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
                t.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                    data=[]
                )
                t.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[]
                )
                t.select.return_value.eq.return_value.eq.return_value.not_.return_value.is_.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[]
                )
            return t

        mock_sb.table.side_effect = table_side_effect

        with pytest.raises(ValueError, match="max_tickets_exceeded"):
            booking_service.validate_booking(
                mock_sb,
                event_id="event-a",
                person_id="p1",
                quantity=1,
                ticket_option_id="opt-1",
                is_checkout=True,
            )
