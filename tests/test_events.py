"""Tests for /api/v1/events/ endpoints."""

from unittest.mock import MagicMock, patch


MOCK_EVENT_RAW = {
    "event_id": "35b43254-4e21-459f-b729-4cb3966cf322",
    "title": "Techno Night Berlin",
    "starts_at": "2026-05-10T22:00:00+00:00",
    "ends_at": None,
    "description": "Eine legendäre Nacht.",
    "category": "Musik",
    "max_capacity": 500,
    "is_public": True,
    "is_free": True,
    "status": "published",
    "invitation_link": "https://happin.app/invite/abc123",
    "created_at": "2026-04-20T10:00:00+00:00",
    "updated_at": "2026-04-20T10:00:00+00:00",
    "location": {
        "location_id": "8fa1205a-aca8-4243-8169-b5af4fd27833",
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
    "event_host": [
        {
            "person": {
                "person_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "supabase_user_id": "uid-host-123",
                "first_name": "Max",
                "last_name": "Mustermann",
            },
        },
    ],
    "event_participation": [
        {
            "event_participation_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
            "status": "Accepted",
            "person": {
                "person_id": "e5f6a7b8-c9d0-1234-5678-abcdef123456",
                "supabase_user_id": "uid-guest-456",
                "first_name": "Anna",
                "last_name": "Schmidt",
            },
        },
    ],
    "ticket_option": [],
}


def _mock_chain(mock_supabase, data):
    """Set up the chained Supabase query mock to return given data."""
    chain = mock_supabase.table.return_value.select.return_value
    # get_public_events: .eq("is_public").eq("status").order().range().execute()
    chain.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = data
    # get_event_by_id: .eq("event_id").maybe_single().execute()
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
    assert event["event_id"] == "35b43254-4e21-459f-b729-4cb3966cf322"
    assert event["title"] == "Techno Night Berlin"
    assert "starts_at" in event
    assert event["image_url"] == "https://example.com/image1.jpg"
    assert event["participant_count"] == 1
    assert event["location"]["city"] == "Berlin"


def test_get_event_detail_found(client, mock_supabase):
    _mock_chain(mock_supabase, [MOCK_EVENT_RAW])
    response = client.get("/api/v1/events/35b43254-4e21-459f-b729-4cb3966cf322")
    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == "35b43254-4e21-459f-b729-4cb3966cf322"
    assert body["host_name"] == "Max Mustermann"
    assert len(body["media_urls"]) == 2
    assert body["invitation_link"] == "https://happin.app/invite/abc123"
    assert "starts_at" in body
    assert body["ends_at"] is None


def test_get_event_detail_not_found(client, mock_supabase):
    _mock_chain(mock_supabase, [])
    response = client.get("/api/v1/events/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_create_event_unauthorized(client, mock_supabase):
    response = client.post("/api/v1/events/", json={
        "title": "Test Event",
        "starts_at": "2026-12-01T18:00:00",
        "is_public": True,
        "location": {"city": "Berlin"},
    })
    assert response.status_code in (401, 403)


def test_create_event_validation_error(client, mock_supabase):
    mock_supabase.auth.get_user.return_value = MagicMock(
        user=MagicMock(id="uid-123", email="test@example.com")
    )
    response = client.post(
        "/api/v1/events/",
        json={"is_public": True},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 422


def test_create_event_success(client, mock_supabase):
    mock_supabase.auth.get_user.return_value = MagicMock(
        user=MagicMock(id="uid-123", email="test@example.com")
    )

    person_chain = MagicMock()
    person_chain.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "person_id": "c1d2e3f4-a5b6-7890-cdef-123456789012",
        "supabase_user_id": "uid-123",
        "email_address": "test@example.com",
        "first_name": "test",
    }

    location_insert = MagicMock()
    location_insert.insert.return_value.execute.return_value.data = [{"location_id": "d2e3f4a5-b6c7-8901-def0-234567890123"}]

    event_insert = MagicMock()
    event_insert.insert.return_value.execute.return_value.data = [{"event_id": "e3f4a5b6-c7d8-9012-ef01-345678901234"}]

    host_insert = MagicMock()
    host_insert.insert.return_value.execute.return_value.data = [
        {"event_host_id": "b8c9d0e1-f2a3-4567-8901-abcdef456789"}
    ]

    created_event_raw = {
        **MOCK_EVENT_RAW,
        "event_id": "e3f4a5b6-c7d8-9012-ef01-345678901234",
        "title": "Neues Event",
    }
    event_select = MagicMock()
    event_select.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = created_event_raw

    call_count = 0

    def table_side_effect(name):
        nonlocal call_count
        idx = call_count
        call_count += 1
        if name == "person":
            return person_chain
        if name == "location":
            return location_insert
        if name == "event" and idx <= 2:
            return event_insert
        if name == "event_host":
            return host_insert
        return event_select

    mock_supabase.table.side_effect = table_side_effect

    response = client.post(
        "/api/v1/events/",
        json={
            "title": "Neues Event",
            "starts_at": "2026-12-01T18:00:00",
            "is_public": True,
            "description": "Test",
            "location": {"city": "Berlin"},
        },
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["event_id"] == "e3f4a5b6-c7d8-9012-ef01-345678901234"
    assert body["title"] == "Neues Event"
