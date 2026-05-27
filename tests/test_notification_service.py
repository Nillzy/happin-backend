"""Tests for notification_service: Fanout-Logik und Lese-API."""

from unittest.mock import MagicMock, patch


EVENT_ID = "11111111-1111-1111-1111-111111111111"
HOST_PERSON_ID = "22222222-2222-2222-2222-222222222222"
PARTICIPANT_A = "33333333-3333-3333-3333-333333333333"
PARTICIPANT_B = "44444444-4444-4444-4444-444444444444"


def _make_admin_mock(*, accepted_persons=(), hosts=(), event_title="Test Event", participant_name=None):
    """Baut ein admin-Supabase-Mock, das alle Abfragen aus notification_service bedient."""
    db = MagicMock()
    insert_calls: list = []
    sub_calls: list = []

    def table(name):
        t = MagicMock()
        if name == "event_participation":
            t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"person_id": pid} for pid in accepted_persons
            ]
        elif name == "event_host":
            t.select.return_value.eq.return_value.execute.return_value.data = [
                {"person_id": pid} for pid in hosts
            ]
        elif name == "event":
            t.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                "title": event_title
            }
        elif name == "person":
            first, last = (participant_name or "Max Mustermann").split(" ", 1) if participant_name else ("Max", "Mustermann")
            t.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                "first_name": first,
                "last_name": last,
            }
        elif name == "notification":
            def _insert(rows):
                insert_calls.append(rows)
                inner = MagicMock()
                inner.execute.return_value = MagicMock(data=rows)
                return inner
            t.insert.side_effect = _insert
        elif name == "web_push_subscription":
            t.select.return_value.in_.return_value.execute.return_value.data = []
            sub_calls.append(t)
        return t

    db.table.side_effect = table
    db._insert_calls = insert_calls
    return db


class TestFanoutEventUpdated:
    def test_inserts_notification_per_accepted_participant(self):
        db = _make_admin_mock(accepted_persons=[PARTICIPANT_A, PARTICIPANT_B])
        with patch("app.services.notification_service.get_supabase_admin", return_value=db):
            from app.services.notification_service import fanout_event_updated
            fanout_event_updated(EVENT_ID, ["title", "starts_at"])

        assert len(db._insert_calls) == 1
        rows = db._insert_calls[0]
        assert len(rows) == 2
        assert {r["recipient_person_id"] for r in rows} == {PARTICIPANT_A, PARTICIPANT_B}
        assert all(r["type"] == "event_updated" for r in rows)
        assert all(r["event_id"] == EVENT_ID for r in rows)
        assert rows[0]["payload"]["changed_fields"] == ["title", "starts_at"]

    def test_no_recipients_no_insert(self):
        db = _make_admin_mock(accepted_persons=[])
        with patch("app.services.notification_service.get_supabase_admin", return_value=db):
            from app.services.notification_service import fanout_event_updated
            fanout_event_updated(EVENT_ID, ["title"])
        assert db._insert_calls == []

    def test_empty_changed_fields_short_circuit(self):
        db = _make_admin_mock(accepted_persons=[PARTICIPANT_A])
        with patch("app.services.notification_service.get_supabase_admin", return_value=db):
            from app.services.notification_service import fanout_event_updated
            fanout_event_updated(EVENT_ID, [])
        assert db._insert_calls == []


class TestFanoutEventCancelled:
    def test_inserts_event_cancelled_for_accepted(self):
        db = _make_admin_mock(accepted_persons=[PARTICIPANT_A])
        with patch("app.services.notification_service.get_supabase_admin", return_value=db):
            from app.services.notification_service import fanout_event_cancelled
            fanout_event_cancelled(EVENT_ID)
        rows = db._insert_calls[0]
        assert rows[0]["type"] == "event_cancelled"
        assert rows[0]["recipient_person_id"] == PARTICIPANT_A
        assert "event_title" in rows[0]["payload"]


class TestFanoutNewParticipant:
    def test_notifies_host_about_new_participant(self):
        db = _make_admin_mock(hosts=[HOST_PERSON_ID], participant_name="Anna Beispiel")
        with patch("app.services.notification_service.get_supabase_admin", return_value=db):
            from app.services.notification_service import fanout_new_participant
            fanout_new_participant(EVENT_ID, PARTICIPANT_A)
        rows = db._insert_calls[0]
        assert len(rows) == 1
        assert rows[0]["recipient_person_id"] == HOST_PERSON_ID
        assert rows[0]["type"] == "new_participant"
        assert rows[0]["payload"]["participant_name"] == "Anna Beispiel"

    def test_does_not_notify_self_when_host_rsvp(self):
        db = _make_admin_mock(hosts=[HOST_PERSON_ID])
        with patch("app.services.notification_service.get_supabase_admin", return_value=db):
            from app.services.notification_service import fanout_new_participant
            fanout_new_participant(EVENT_ID, HOST_PERSON_ID)
        assert db._insert_calls == []


class TestListAndMarkRead:
    def test_unread_count_returns_count(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value.count = 7
        with patch("app.services.notification_service.get_supabase_for_user", return_value=sb):
            from app.services.notification_service import unread_count
            assert unread_count(PARTICIPANT_A, "tok") == 7

    def test_mark_read_returns_true_when_row_updated(self):
        sb = MagicMock()
        sb.table.return_value.update.return_value.eq.return_value.eq.return_value.is_.return_value.execute.return_value.data = [
            {"notification_id": "n1"}
        ]
        with patch("app.services.notification_service.get_supabase_for_user", return_value=sb):
            from app.services.notification_service import mark_read
            assert mark_read("n1", PARTICIPANT_A, "tok") is True

    def test_mark_read_returns_false_when_no_row(self):
        sb = MagicMock()
        sb.table.return_value.update.return_value.eq.return_value.eq.return_value.is_.return_value.execute.return_value.data = []
        with patch("app.services.notification_service.get_supabase_for_user", return_value=sb):
            from app.services.notification_service import mark_read
            assert mark_read("n-missing", PARTICIPANT_A, "tok") is False

    def test_mark_all_read_returns_count(self):
        sb = MagicMock()
        sb.table.return_value.update.return_value.eq.return_value.is_.return_value.execute.return_value.data = [
            {"notification_id": "n1"}, {"notification_id": "n2"}, {"notification_id": "n3"}
        ]
        with patch("app.services.notification_service.get_supabase_for_user", return_value=sb):
            from app.services.notification_service import mark_all_read
            assert mark_all_read(PARTICIPANT_A, "tok") == 3
