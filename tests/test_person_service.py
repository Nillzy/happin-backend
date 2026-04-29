"""Tests for person_service."""

from unittest.mock import MagicMock, patch


@patch("app.services.person_service.get_supabase_for_user")
def test_get_existing_person(mock_get_client):
    mock_supabase = MagicMock()
    mock_get_client.return_value = mock_supabase

    existing = {
        "person_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "supabase_user_id": "uid-abc",
        "email_address": "user@example.com",
        "first_name": "user",
    }
    person_table = MagicMock()
    person_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=existing)
    mock_supabase.table.return_value = person_table

    from app.services.person_service import get_or_create_person

    result = get_or_create_person("uid-abc", "user@example.com", "fake-token")
    assert result["person_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert result["supabase_user_id"] == "uid-abc"
    person_table.insert.assert_not_called()


@patch("app.services.person_service.get_supabase_for_user")
def test_create_new_person(mock_get_client):
    mock_supabase = MagicMock()
    mock_get_client.return_value = mock_supabase

    person_table = MagicMock()
    person_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = None

    new_person = {
        "person_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "supabase_user_id": "uid-new",
        "email_address": "new@example.com",
        "first_name": "new",
    }
    person_table.insert.return_value.execute.return_value = MagicMock(data=[new_person])
    mock_supabase.table.return_value = person_table

    from app.services.person_service import get_or_create_person

    result = get_or_create_person("uid-new", "new@example.com", "fake-token")
    assert result["person_id"] == "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    assert result["first_name"] == "new"
