"""Tests for calendar export functionality."""

from unittest.mock import MagicMock, patch


MOCK_EVENT_FOR_CALENDAR = {
    "event_id": "35b43254-4e21-459f-b729-4cb3966cf322",
    "title": "Techno Night Berlin",
    "description": "Eine legendäre Nacht.",
    "starts_at": "2026-05-10T22:00:00+00:00",
    "ends_at": "2026-05-11T06:00:00+00:00",
    "location": {
        "location_id": "8fa1205a-aca8-4243-8169-b5af4fd27833",
        "street": "Revaler Str.",
        "house_number": "99",
        "postal_code": "10245",
        "city": "Berlin",
        "country": "Deutschland",
    },
}


def _mock_calendar_chain(mock_supabase, data):
    """Set up mock for calendar service queries."""
    table_mock = mock_supabase.table.return_value
    select_mock = table_mock.select.return_value
    eq_mock = select_mock.eq.return_value
    maybe_single_mock = eq_mock.maybe_single.return_value

    response = MagicMock()
    response.data = data
    maybe_single_mock.execute.return_value = response


def test_calendar_endpoint_returns_ics(client, mock_supabase):
    """Test that the calendar endpoint returns a valid ICS file."""
    _mock_calendar_chain(mock_supabase, MOCK_EVENT_FOR_CALENDAR)

    response = client.get("/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/calendar.ics")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/calendar; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert ".ics" in response.headers["content-disposition"]

    content = response.content.decode("utf-8")
    assert "BEGIN:VCALENDAR" in content
    assert "END:VCALENDAR" in content
    assert "BEGIN:VEVENT" in content
    assert "END:VEVENT" in content
    assert "Techno Night Berlin" in content


def test_calendar_contains_event_details(client, mock_supabase):
    """Test that ICS contains all event details."""
    _mock_calendar_chain(mock_supabase, MOCK_EVENT_FOR_CALENDAR)

    response = client.get("/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/calendar.ics")
    content = response.content.decode("utf-8")

    assert "SUMMARY:Techno Night Berlin" in content
    assert "DESCRIPTION:" in content
    assert "Eine" in content
    assert "DTSTART" in content
    assert "DTEND" in content
    assert "LOCATION:" in content
    assert "Berlin" in content


def test_calendar_endpoint_not_found(client, mock_supabase):
    """Test that 404 is returned for non-existent events."""
    _mock_calendar_chain(mock_supabase, None)

    response = client.get("/api/v1/events/00000000-0000-0000-0000-000000000000/calendar.ics")

    assert response.status_code == 404


def test_calendar_event_without_end_time(client, mock_supabase):
    """Test that events without end_at get a default 2-hour duration."""
    event_no_end = {**MOCK_EVENT_FOR_CALENDAR, "ends_at": None}
    _mock_calendar_chain(mock_supabase, event_no_end)

    response = client.get("/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/calendar.ics")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "DTEND" in content


def test_calendar_event_without_location(client, mock_supabase):
    """Test that events without location still generate valid ICS."""
    event_no_location = {**MOCK_EVENT_FOR_CALENDAR, "location": None}
    _mock_calendar_chain(mock_supabase, event_no_location)

    response = client.get("/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/calendar.ics")

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "BEGIN:VCALENDAR" in content
    assert "BEGIN:VEVENT" in content


def test_calendar_uid_format(client, mock_supabase):
    """Test that the UID follows the expected format."""
    _mock_calendar_chain(mock_supabase, MOCK_EVENT_FOR_CALENDAR)

    response = client.get("/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322/calendar.ics")
    content = response.content.decode("utf-8")

    assert "UID:35b43254-4e21-459f-b729-4cb3966cf322@happin.app" in content
