"""Tests for filter query parameters on GET /api/v1/events/."""

from unittest.mock import MagicMock


# Two mock events with different city and category
MOCK_BERLIN = {
    "event_id": "aaaa0000-0000-0000-0000-000000000001",
    "title": "Berlin Musik Night",
    "starts_at": "2099-06-01T20:00:00+00:00",
    "ends_at": None,
    "description": None,
    "category": "Musik",
    "max_capacity": None,
    "is_public": True,
    "is_free": True,
    "status": "published",
    "invitation_link": None,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
    "location": {"location_id": "loc-1", "city": "Berlin"},
    "event_media": [],
    "event_host": [],
    "ticket_option": [],
    "ticket": [],
}

MOCK_MUNICH = {
    "event_id": "bbbb0000-0000-0000-0000-000000000002",
    "title": "München Sport Event",
    "starts_at": "2099-06-02T10:00:00+00:00",
    "ends_at": None,
    "description": None,
    "category": "Sport",
    "max_capacity": None,
    "is_public": True,
    "is_free": False,
    "status": "published",
    "invitation_link": None,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
    "location": {"location_id": "loc-2", "city": "München"},
    "event_media": [],
    "event_host": [],
    "ticket_option": [],
    "ticket": [],
}


def _setup_flexible_chain(mock_supabase, data):
    """Set up a Supabase mock chain that works regardless of filter method order."""
    execute_response = MagicMock()
    execute_response.data = data
    execute_response.count = len(data)

    chain = MagicMock()
    chain.execute.return_value = execute_response
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.lte.return_value = chain
    chain.filter.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.ilike.return_value = chain
    chain.maybe_single.return_value = chain

    mock_supabase.table.return_value.select.return_value = chain


def test_filter_by_city(client, mock_supabase, auth_headers):
    _setup_flexible_chain(mock_supabase, [MOCK_BERLIN, MOCK_MUNICH])
    response = client.get("/api/v1/events/?city=Berlin", headers=auth_headers)
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 1
    assert events[0]["event_id"] == MOCK_BERLIN["event_id"]


def test_filter_by_city_case_insensitive(client, mock_supabase, auth_headers):
    _setup_flexible_chain(mock_supabase, [MOCK_BERLIN, MOCK_MUNICH])
    response = client.get("/api/v1/events/?city=berlin", headers=auth_headers)
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 1
    assert events[0]["location"]["city"] == "Berlin"


def test_filter_by_category(client, mock_supabase, auth_headers):
    _setup_flexible_chain(mock_supabase, [MOCK_BERLIN, MOCK_MUNICH])
    response = client.get("/api/v1/events/?categories=Musik", headers=auth_headers)
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 1
    assert events[0]["event_id"] == MOCK_BERLIN["event_id"]


def test_filter_by_multiple_categories(client, mock_supabase, auth_headers):
    _setup_flexible_chain(mock_supabase, [MOCK_BERLIN, MOCK_MUNICH])
    response = client.get("/api/v1/events/?categories=Musik,Sport", headers=auth_headers)
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 2


def test_filter_by_is_free(client, mock_supabase, auth_headers):
    # Supabase mock returns only the free event (is_free filter applied at DB level)
    _setup_flexible_chain(mock_supabase, [MOCK_BERLIN])
    response = client.get("/api/v1/events/?is_free=true", headers=auth_headers)
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 1
    assert events[0]["is_free"] is True


def test_no_filter_returns_all(client, mock_supabase, auth_headers):
    _setup_flexible_chain(mock_supabase, [MOCK_BERLIN, MOCK_MUNICH])
    response = client.get("/api/v1/events/", headers=auth_headers)
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 2


def test_filter_city_no_match(client, mock_supabase, auth_headers):
    _setup_flexible_chain(mock_supabase, [MOCK_BERLIN, MOCK_MUNICH])
    response = client.get("/api/v1/events/?city=Hamburg", headers=auth_headers)
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 0
