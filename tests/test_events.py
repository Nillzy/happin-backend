"""Tests for /api/v1/events/ endpoints."""

from unittest.mock import MagicMock


MOCK_EVENT_RAW = {
    "event_id": 1,
    "title": "Techno Night Berlin",
    "date": "2026-05-10T22:00:00",
    "description": "Eine legendäre Nacht.",
    "category": "Musik",
    "max_capacity": 500,
    "is_public": True,
    "invitation_link": "https://happin.app/invite/abc123",
    "created_at": "2026-04-20T10:00:00",
    "updated_at": "2026-04-20T10:00:00",
    "location": {
        "location_id": 1,
        "city": "Berlin",
        "street": "Revaler Str.",
        "house_number": "99",
        "postal_code": "10245",
        "country": "Deutschland",
        "type": "Club",
    },
    "event_media": [
        {"media_url": "https://example.com/image1.jpg"},
        {"media_url": "https://example.com/image2.jpg"},
    ],
    "event_participation": [
        {
            "event_participation_id": 1,
            "role": "Host",
            "person": {"first_name": "Max", "last_name": "Mustermann"},
        },
        {
            "event_participation_id": 2,
            "role": "Participant",
            "person": {"first_name": "Anna", "last_name": "Schmidt"},
        },
    ],
}


def _mock_chain(mock_supabase, data):
    """Set up the chained Supabase query mock to return given data."""
    chain = mock_supabase.table.return_value.select.return_value
    chain.eq.return_value.order.return_value.range.return_value.execute.return_value.data = data
    chain.eq.return_value.maybe_single.return_value.execute.return_value.data = (
        data[0] if data else None
    )


def test_list_events_empty(client, mock_supabase):
    _mock_chain(mock_supabase, [])
    response = client.get("/api/v1/events/")
    assert response.status_code == 200
    body = response.json()
    assert body["events"] == []
    assert body["count"] == 0


def test_list_events_returns_data(client, mock_supabase):
    _mock_chain(mock_supabase, [MOCK_EVENT_RAW])
    response = client.get("/api/v1/events/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    event = body["events"][0]
    assert event["event_id"] == 1
    assert event["title"] == "Techno Night Berlin"
    assert event["image_url"] == "https://example.com/image1.jpg"
    assert event["participant_count"] == 2
    assert event["location"]["city"] == "Berlin"


def test_get_event_detail_found(client, mock_supabase):
    _mock_chain(mock_supabase, [MOCK_EVENT_RAW])
    response = client.get("/api/v1/events/1")
    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == 1
    assert body["host_name"] == "Max Mustermann"
    assert len(body["media_urls"]) == 2
    assert body["invitation_link"] == "https://happin.app/invite/abc123"


def test_get_event_detail_not_found(client, mock_supabase):
    _mock_chain(mock_supabase, [])
    response = client.get("/api/v1/events/999")
    assert response.status_code == 404
