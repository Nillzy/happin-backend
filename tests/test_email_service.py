"""Behavior-driven tests for email_service.

These tests verify observable behavior:
- Settings/Resend integration (api_key is set before send)
- Send is skipped when RESEND_API_KEY is unset
- HTML escaping for user-provided fields (XSS protection)
- Error handling: exceptions from resend.Emails.send are logged but not re-raised

Fixtures (`resend_configured`, `resend_unconfigured`) keep the
`patch.object(settings, ...)` setup out of every single test body — one
source of truth, no copy-paste drift between scenarios.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services import email_service


# ---------------------------------------------------------------------------
# Fixtures — single source of truth for Resend setup
# ---------------------------------------------------------------------------


@pytest.fixture
def resend_configured():
    """Yield a mock `resend.Emails.send` with RESEND_API_KEY/FROM set."""
    with patch.object(
        email_service.settings, "RESEND_API_KEY", "test-key"
    ), patch.object(
        email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
    ), patch(
        "app.services.email_service.resend.Emails.send"
    ) as mock_send:
        yield mock_send


@pytest.fixture
def resend_unconfigured():
    """Yield a mock `resend.Emails.send` with RESEND_API_KEY empty."""
    with patch.object(email_service.settings, "RESEND_API_KEY", ""), patch(
        "app.services.email_service.resend.Emails.send"
    ) as mock_send:
        yield mock_send


@pytest.fixture
def resend_module_patched():
    """Yield the entire `resend` module mock so api_key assignment is observable."""
    with patch.object(
        email_service.settings, "RESEND_API_KEY", "configured-key"
    ), patch.object(
        email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
    ), patch(
        "app.services.email_service.resend"
    ) as mock_resend:
        yield mock_resend


@pytest.fixture
def promotion_payload():
    """Canonical kwargs for send_waitlist_promotion_email."""
    return dict(
        email="user@example.com",
        name="Alice",
        event_title="Concert",
        event_link="https://app.happin.test/event/1",
        expires_at=datetime(2026, 7, 1, 14, 30),
    )


@pytest.fixture
def confirmation_payload():
    """Canonical kwargs for send_waitlist_confirmation_email."""
    return dict(
        email="user@example.com",
        name="Alice",
        event_title="Concert",
    )


# ---------------------------------------------------------------------------
# send_waitlist_promotion_email
# ---------------------------------------------------------------------------


class TestSendWaitlistPromotionEmail:
    """Tests for email_service.send_waitlist_promotion_email."""

    def test_should_send_email_when_api_key_is_configured(
        self, resend_configured, promotion_payload
    ):
        email_service.send_waitlist_promotion_email(**promotion_payload)

        resend_configured.assert_called_once()
        params = resend_configured.call_args[0][0]
        assert params["to"] == ["user@example.com"]
        assert "Concert" in params["subject"]

    def test_should_skip_send_when_api_key_is_missing(
        self, resend_unconfigured, promotion_payload
    ):
        email_service.send_waitlist_promotion_email(**promotion_payload)

        resend_unconfigured.assert_not_called()

    def test_should_set_resend_api_key_before_send(
        self, resend_module_patched, promotion_payload
    ):
        """The Resend SDK reads api_key from a module-level attribute."""
        email_service.send_waitlist_promotion_email(**promotion_payload)

        assert resend_module_patched.api_key == "configured-key"
        resend_module_patched.Emails.send.assert_called_once()

    def test_should_html_escape_user_supplied_name(
        self, resend_configured, promotion_payload
    ):
        promotion_payload["name"] = "<script>alert('xss')</script>"
        email_service.send_waitlist_promotion_email(**promotion_payload)

        params = resend_configured.call_args[0][0]
        assert "<script>" not in params["html"]
        assert "&lt;script&gt;" in params["html"]

    def test_should_html_escape_event_title(
        self, resend_configured, promotion_payload
    ):
        promotion_payload["event_title"] = "<img src=x onerror=alert(1)>"
        email_service.send_waitlist_promotion_email(**promotion_payload)

        params = resend_configured.call_args[0][0]
        assert "<img" not in params["html"]
        assert "&lt;img" in params["html"]

    def test_should_format_deadline_in_german_locale(
        self, resend_configured, promotion_payload
    ):
        email_service.send_waitlist_promotion_email(**promotion_payload)

        params = resend_configured.call_args[0][0]
        # German-style: DD.MM.YYYY HH:MM Uhr
        assert "01.07.2026 14:30 Uhr" in params["html"]

    def test_should_not_raise_when_resend_send_throws(self, promotion_payload):
        """Resend exceptions are logged but must not propagate to caller."""
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch(
            "app.services.email_service.resend.Emails.send",
            side_effect=RuntimeError("API down"),
        ):
            # Must not raise
            email_service.send_waitlist_promotion_email(**promotion_payload)

    def test_should_handle_empty_event_link_gracefully(
        self, resend_configured, promotion_payload
    ):
        promotion_payload["event_link"] = ""
        email_service.send_waitlist_promotion_email(**promotion_payload)

        resend_configured.assert_called_once()

    def test_should_use_configured_from_email_as_sender(
        self, resend_configured, promotion_payload
    ):
        # Override FROM via the same settings module
        with patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "custom@happin.test"
        ):
            email_service.send_waitlist_promotion_email(**promotion_payload)

        params = resend_configured.call_args[0][0]
        assert params["from"] == "custom@happin.test"

    def test_should_log_warning_when_api_key_missing(
        self, resend_unconfigured, promotion_payload, caplog
    ):
        with caplog.at_level("WARNING"):
            email_service.send_waitlist_promotion_email(**promotion_payload)

        assert any(
            "RESEND_API_KEY not set" in rec.message for rec in caplog.records
        )


# ---------------------------------------------------------------------------
# send_waitlist_confirmation_email
# ---------------------------------------------------------------------------


class TestSendWaitlistConfirmationEmail:
    """Tests for email_service.send_waitlist_confirmation_email."""

    def test_should_send_email_when_api_key_is_configured(
        self, resend_configured, confirmation_payload
    ):
        email_service.send_waitlist_confirmation_email(**confirmation_payload)

        resend_configured.assert_called_once()
        params = resend_configured.call_args[0][0]
        assert params["to"] == ["user@example.com"]

    def test_should_skip_send_when_api_key_is_missing(
        self, resend_unconfigured, confirmation_payload
    ):
        email_service.send_waitlist_confirmation_email(**confirmation_payload)

        resend_unconfigured.assert_not_called()

    def test_should_set_api_key_before_send(
        self, resend_module_patched, confirmation_payload
    ):
        # Override the api_key for this specific scenario
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "confirm-key"
        ):
            email_service.send_waitlist_confirmation_email(**confirmation_payload)

        assert resend_module_patched.api_key == "confirm-key"

    def test_should_html_escape_user_name_against_xss(
        self, resend_configured, confirmation_payload
    ):
        confirmation_payload["name"] = "<b>injected</b>"
        email_service.send_waitlist_confirmation_email(**confirmation_payload)

        params = resend_configured.call_args[0][0]
        assert "<b>injected</b>" not in params["html"]
        assert "&lt;b&gt;injected&lt;/b&gt;" in params["html"]

    def test_should_html_escape_event_title_against_xss(
        self, resend_configured, confirmation_payload
    ):
        confirmation_payload["event_title"] = "<script>evil()</script>"
        email_service.send_waitlist_confirmation_email(**confirmation_payload)

        params = resend_configured.call_args[0][0]
        assert "<script>" not in params["html"]

    def test_should_not_raise_when_resend_throws(self, confirmation_payload):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch(
            "app.services.email_service.resend.Emails.send",
            side_effect=Exception("network error"),
        ):
            # Must not raise
            email_service.send_waitlist_confirmation_email(**confirmation_payload)

    def test_should_include_event_title_in_subject(
        self, resend_configured, confirmation_payload
    ):
        confirmation_payload["event_title"] = "Summer Festival"
        email_service.send_waitlist_confirmation_email(**confirmation_payload)

        params = resend_configured.call_args[0][0]
        assert "Summer Festival" in params["subject"]

    def test_should_log_warning_when_api_key_missing(
        self, resend_unconfigured, confirmation_payload, caplog
    ):
        with caplog.at_level("WARNING"):
            email_service.send_waitlist_confirmation_email(**confirmation_payload)

        assert any(
            "RESEND_API_KEY not set" in rec.message for rec in caplog.records
        )

    def test_should_use_configured_from_email_as_sender(
        self, resend_configured, confirmation_payload
    ):
        with patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "custom@happin.test"
        ):
            email_service.send_waitlist_confirmation_email(**confirmation_payload)

        params = resend_configured.call_args[0][0]
        assert params["from"] == "custom@happin.test"
