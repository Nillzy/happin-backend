"""Unit-Tests: Push-Token / Web-Subscription Ownership-Transfer beim Login.

Verifiziert, dass beim Upsert über den Admin-Client gegangen wird (RLS-Bypass)
und die Constraint pro Gerät (token / endpoint) geht — nicht mehr per
(person_id, …). Damit kann ein zweiter User auf demselben Gerät die Zeile
übernehmen statt eine Dublette zu erzeugen.
"""

from unittest.mock import MagicMock, patch


def _make_admin_table_mock():
    """Erzeugt einen Supabase-Admin-Mock, der `.table().upsert(...).execute()` toleriert."""
    admin = MagicMock()
    chain = admin.table.return_value
    chain.upsert.return_value.execute.return_value = MagicMock(data=[])
    return admin, chain


def test_expo_upsert_uses_admin_client_with_on_conflict_token():
    from app.services import expo_push_service

    admin, chain = _make_admin_table_mock()
    with patch(
        "app.services.expo_push_service.get_supabase_admin",
        return_value=admin,
    ):
        expo_push_service.upsert_token(
            person_id="p-new",
            token="ExponentPushToken[abc]",
            platform="ios",
            user_agent="ios 17.0",
            auth_token="bearer-xyz",
        )

    admin.table.assert_called_once_with("expo_push_token")
    args, kwargs = chain.upsert.call_args
    # Payload enthält neue person_id
    assert args[0]["person_id"] == "p-new"
    assert args[0]["token"] == "ExponentPushToken[abc]"
    # On-Conflict ist auf token (nicht person_id,token) — Voraussetzung für Ownership-Transfer
    assert kwargs.get("on_conflict") == "token"


def test_web_upsert_uses_admin_client_with_on_conflict_endpoint():
    from app.services import reminder_service

    admin, chain = _make_admin_table_mock()
    with patch(
        "app.services.reminder_service.get_supabase_admin",
        return_value=admin,
    ):
        reminder_service.upsert_subscription(
            person_id="p-new",
            token="bearer-xyz",
            endpoint="https://fcm.googleapis.com/fcm/send/abc",
            p256dh="p256dh-key",
            auth="auth-key",
            user_agent="Mozilla/5.0",
        )

    admin.table.assert_called_once_with("web_push_subscription")
    args, kwargs = chain.upsert.call_args
    assert args[0]["person_id"] == "p-new"
    assert args[0]["endpoint"] == "https://fcm.googleapis.com/fcm/send/abc"
    assert kwargs.get("on_conflict") == "endpoint"


def test_expo_upsert_does_not_call_user_agent_dedupe_delete():
    """Die alte `user_agent`-basierte Pre-Delete-Phase darf nicht mehr existieren —
    sonst werden zwei iPhones mit gleicher iOS-Version weiter gegenseitig gelöscht."""
    from app.services import expo_push_service

    admin, chain = _make_admin_table_mock()
    with patch(
        "app.services.expo_push_service.get_supabase_admin",
        return_value=admin,
    ):
        expo_push_service.upsert_token(
            person_id="p",
            token="t",
            platform="ios",
            user_agent="ios 17.0",
            auth_token="bearer",
        )

    # Es darf KEIN .delete()-Aufruf vor dem Upsert kommen.
    chain.delete.assert_not_called()


def test_web_upsert_does_not_call_user_agent_dedupe_delete():
    from app.services import reminder_service

    admin, chain = _make_admin_table_mock()
    with patch(
        "app.services.reminder_service.get_supabase_admin",
        return_value=admin,
    ):
        reminder_service.upsert_subscription(
            person_id="p",
            token="bearer",
            endpoint="https://e",
            p256dh="x",
            auth="y",
            user_agent="UA",
        )

    chain.delete.assert_not_called()
