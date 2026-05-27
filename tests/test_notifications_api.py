"""Integrationstests für /me/notifications Endpoints."""

from unittest.mock import MagicMock, patch


PERSON_ID = "p-test"
NOTIF_ID = "n-1234"


def test_unread_count_endpoint(client, auth_headers):
    with patch(
        "app.api.v1.notifications.notification_service.unread_count",
        return_value=5,
    ), patch(
        "app.api.v1.notifications.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.get("/api/v1/users/me/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"count": 5}


def test_list_endpoint_returns_items(client, auth_headers):
    rows = [
        {
            "notification_id": NOTIF_ID,
            "event_id": "e-1",
            "type": "event_updated",
            "payload": {"event_title": "Foo"},
            "created_at": "2026-05-27T10:00:00+00:00",
            "read_at": None,
        }
    ]
    with patch(
        "app.api.v1.notifications.notification_service.list_for_person",
        return_value=rows,
    ), patch(
        "app.api.v1.notifications.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.get("/api/v1/users/me/notifications", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["notification_id"] == NOTIF_ID
    assert body["items"][0]["type"] == "event_updated"


def test_mark_one_read_returns_204(client, auth_headers):
    with patch(
        "app.api.v1.notifications.notification_service.mark_read",
        return_value=True,
    ), patch(
        "app.api.v1.notifications.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.post(f"/api/v1/users/me/notifications/{NOTIF_ID}/read", headers=auth_headers)
    assert resp.status_code == 204


def test_mark_one_read_returns_404_when_missing(client, auth_headers):
    with patch(
        "app.api.v1.notifications.notification_service.mark_read",
        return_value=False,
    ), patch(
        "app.api.v1.notifications.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.post("/api/v1/users/me/notifications/missing/read", headers=auth_headers)
    assert resp.status_code == 404


def test_mark_all_read_returns_count(client, auth_headers):
    with patch(
        "app.api.v1.notifications.notification_service.mark_all_read",
        return_value=4,
    ), patch(
        "app.api.v1.notifications.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.post("/api/v1/users/me/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"marked": 4}


def test_list_endpoint_rejects_invalid_limit(client, auth_headers):
    with patch(
        "app.api.v1.notifications.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.get("/api/v1/users/me/notifications?limit=999", headers=auth_headers)
    assert resp.status_code == 400
