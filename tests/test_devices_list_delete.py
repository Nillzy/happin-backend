"""Tests für Geräte-Verwaltung: List + Delete-by-id für Web-Subs und Expo-Tokens."""

from unittest.mock import patch


PERSON_ID = "p-test"


def test_list_web_push_subscriptions(client, auth_headers):
    rows = [
        {
            "web_push_subscription_id": "sub-1",
            "endpoint": "https://fcm.googleapis.com/fcm/send/abc",
            "user_agent": "Mozilla/5.0 (Macintosh)",
            "created_at": "2026-05-26T10:00:00+00:00",
        }
    ]
    with patch(
        "app.api.v1.reminders.reminder_service.list_subscriptions",
        return_value=rows,
    ), patch(
        "app.api.v1.reminders.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.get(
            "/api/v1/users/me/web-push-subscriptions", headers=auth_headers
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["web_push_subscription_id"] == "sub-1"
    # Sensitive Felder dürfen NICHT in der Response auftauchen.
    assert "p256dh_key" not in body["items"][0]
    assert "auth_key" not in body["items"][0]


def test_list_expo_push_tokens(client, auth_headers):
    rows = [
        {
            "expo_push_token_id": "tok-1",
            "platform": "ios",
            "user_agent": "ios 17.0",
            "created_at": "2026-05-26T10:00:00+00:00",
        }
    ]
    with patch(
        "app.api.v1.reminders.expo_push_service.list_tokens",
        return_value=rows,
    ), patch(
        "app.api.v1.reminders.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.get(
            "/api/v1/users/me/expo-push-tokens", headers=auth_headers
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["expo_push_token_id"] == "tok-1"
    # Der vollständige Token darf NICHT in der Response auftauchen.
    assert "token" not in body["items"][0]


def test_delete_web_push_subscription_by_id_returns_204(client, auth_headers):
    with patch(
        "app.api.v1.reminders.reminder_service.delete_subscription_by_id",
        return_value=True,
    ), patch(
        "app.api.v1.reminders.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.delete(
            "/api/v1/users/me/web-push-subscriptions/sub-1", headers=auth_headers
        )
    assert resp.status_code == 204


def test_delete_web_push_subscription_by_id_returns_404_when_missing(
    client, auth_headers
):
    with patch(
        "app.api.v1.reminders.reminder_service.delete_subscription_by_id",
        return_value=False,
    ), patch(
        "app.api.v1.reminders.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.delete(
            "/api/v1/users/me/web-push-subscriptions/missing", headers=auth_headers
        )
    assert resp.status_code == 404


def test_delete_expo_push_token_by_id_returns_204(client, auth_headers):
    with patch(
        "app.api.v1.reminders.expo_push_service.delete_token_by_id",
        return_value=True,
    ), patch(
        "app.api.v1.reminders.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.delete(
            "/api/v1/users/me/expo-push-tokens/tok-1", headers=auth_headers
        )
    assert resp.status_code == 204


def test_delete_expo_push_token_by_id_returns_404_when_missing(client, auth_headers):
    with patch(
        "app.api.v1.reminders.expo_push_service.delete_token_by_id",
        return_value=False,
    ), patch(
        "app.api.v1.reminders.person_service.get_or_create_person",
        return_value={"person_id": PERSON_ID},
    ):
        resp = client.delete(
            "/api/v1/users/me/expo-push-tokens/missing", headers=auth_headers
        )
    assert resp.status_code == 404
