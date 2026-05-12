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
