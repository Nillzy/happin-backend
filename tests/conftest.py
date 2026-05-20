import os

# Must be set before any app import so pydantic-settings doesn't fail
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key-for-testing")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Single shared mock instance used across all tests
_mock_supabase = MagicMock()

# Patch create_client before importing app so the module-level call doesn't
# try to open a real network connection to Supabase.
with patch("supabase.create_client", return_value=_mock_supabase):
    from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Reset and return the shared mock Supabase client."""
    _mock_supabase.reset_mock(side_effect=True, return_value=True)
    return _mock_supabase


@pytest.fixture
def auth_headers(mock_supabase):
    """Authenticated request headers + mocked auth.get_user and person lookup.

    Use in tests that hit endpoints requiring `get_current_user`.
    """
    mock_supabase.auth.get_user.return_value = MagicMock(
        user=MagicMock(id="uid-test", email="test@example.com")
    )
    with patch(
        "app.api.v1.events.person_service.get_or_create_person",
        return_value={
            "person_id": "p-test",
            "supabase_user_id": "uid-test",
            "email_address": "test@example.com",
            "first_name": "Test",
        },
    ):
        yield {"Authorization": "Bearer fake-token"}
