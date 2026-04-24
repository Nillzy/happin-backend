"""Tests for /api/v1/user/me authentication endpoint."""

from datetime import datetime
from unittest.mock import MagicMock


def test_user_me_no_token(client):
    """Without Authorization header, HTTPBearer returns 403."""
    response = client.get("/api/v1/user/me")
    assert response.status_code == 403


def test_user_me_invalid_token(client, mock_supabase):
    """Invalid/expired token causes Supabase to raise → 401."""
    mock_supabase.auth.get_user.side_effect = Exception("Invalid JWT")

    response = client.get(
        "/api/v1/user/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_user_me_valid_token(client, mock_supabase):
    """Valid token returns the user profile."""
    mock_user = MagicMock()
    mock_user.user.id = "user-123"
    mock_user.user.phone = "+49123456789"
    mock_user.user.email = "test@example.com"
    mock_user.user.created_at = datetime(2024, 1, 1, 12, 0, 0)

    mock_supabase.auth.get_user.return_value = mock_user
    mock_supabase.auth.get_user.side_effect = None

    response = client.get(
        "/api/v1/user/me",
        headers={"Authorization": "Bearer valid-mock-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "user-123"
    assert data["phone"] == "+49123456789"
    assert data["email"] == "test@example.com"
