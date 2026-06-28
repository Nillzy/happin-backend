"""Behavior-driven tests for email_service.

These tests verify observable behavior:
- Settings/Resend integration (api_key is set before send)
- Send is skipped when RESEND_API_KEY is unset
- HTML escaping for user-provided fields (XSS protection)
- Error handling: exceptions from resend.Emails.send are logged but not re-raised
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services import email_service


# ---------------------------------------------------------------------------
# send_waitlist_promotion_email
# ---------------------------------------------------------------------------


class TestSendWaitlistPromotionEmail:
    """Tests for email_service.send_waitlist_promotion_email."""

    def test_should_send_email_when_api_key_is_configured(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_promotion_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
                event_link="https://app.happin.test/event/1",
                expires_at=datetime(2026, 7, 1, 14, 30),
            )

            mock_send.assert_called_once()
            params = mock_send.call_args[0][0]
            assert params["to"] == ["user@example.com"]
            assert "Concert" in params["subject"]

    def test_should_skip_send_when_api_key_is_missing(self):
        with patch.object(email_service.settings, "RESEND_API_KEY", ""), patch(
            "app.services.email_service.resend.Emails.send"
        ) as mock_send:
            email_service.send_waitlist_promotion_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
                event_link="https://app.happin.test/event/1",
                expires_at=datetime(2026, 7, 1, 14, 30),
            )

            mock_send.assert_not_called()

    def test_should_set_resend_api_key_before_send(self):
        """The Resend SDK reads api_key from a module-level attribute."""
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "configured-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend") as mock_resend:
            email_service.send_waitlist_promotion_email(
                email="user@example.com",
                name="Bob",
                event_title="Party",
                event_link="https://app.happin.test/event/2",
                expires_at=datetime(2026, 8, 1, 18, 0),
            )

            assert mock_resend.api_key == "configured-key"
            mock_resend.Emails.send.assert_called_once()

    def test_should_html_escape_user_supplied_name(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_promotion_email(
                email="user@example.com",
                name="<script>alert('xss')</script>",
                event_title="Concert",
                event_link="https://app.happin.test/event/1",
                expires_at=datetime(2026, 7, 1, 14, 30),
            )

            params = mock_send.call_args[0][0]
            assert "<script>" not in params["html"]
            assert "&lt;script&gt;" in params["html"]

    def test_should_html_escape_event_title(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_promotion_email(
                email="user@example.com",
                name="Alice",
                event_title="<img src=x onerror=alert(1)>",
                event_link="https://app.happin.test/event/1",
                expires_at=datetime(2026, 7, 1, 14, 30),
            )

            params = mock_send.call_args[0][0]
            assert "<img" not in params["html"]
            assert "&lt;img" in params["html"]

    def test_should_format_deadline_in_german_locale(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_promotion_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
                event_link="https://app.happin.test/event/1",
                expires_at=datetime(2026, 7, 1, 14, 30),
            )

            params = mock_send.call_args[0][0]
            # German-style: DD.MM.YYYY HH:MM Uhr
            assert "01.07.2026 14:30 Uhr" in params["html"]

    def test_should_not_raise_when_resend_send_throws(self):
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
            email_service.send_waitlist_promotion_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
                event_link="https://app.happin.test/event/1",
                expires_at=datetime(2026, 7, 1, 14, 30),
            )

    def test_should_handle_empty_event_link_gracefully(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_promotion_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
                event_link="",
                expires_at=datetime(2026, 7, 1, 14, 30),
            )

            mock_send.assert_called_once()

    def test_should_use_configured_from_email_as_sender(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "custom@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_promotion_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
                event_link="https://app.happin.test/event/1",
                expires_at=datetime(2026, 7, 1, 14, 30),
            )

            params = mock_send.call_args[0][0]
            assert params["from"] == "custom@happin.test"

    def test_should_log_warning_when_api_key_missing(self, caplog):
        with patch.object(email_service.settings, "RESEND_API_KEY", ""):
            with caplog.at_level("WARNING"):
                email_service.send_waitlist_promotion_email(
                    email="user@example.com",
                    name="Alice",
                    event_title="Concert",
                    event_link="https://app.happin.test/event/1",
                    expires_at=datetime(2026, 7, 1, 14, 30),
                )

            assert any(
                "RESEND_API_KEY not set" in rec.message for rec in caplog.records
            )


# ---------------------------------------------------------------------------
# send_waitlist_confirmation_email
# ---------------------------------------------------------------------------


class TestSendWaitlistConfirmationEmail:
    """Tests for email_service.send_waitlist_confirmation_email."""

    def test_should_send_email_when_api_key_is_configured(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_confirmation_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
            )

            mock_send.assert_called_once()
            params = mock_send.call_args[0][0]
            assert params["to"] == ["user@example.com"]

    def test_should_skip_send_when_api_key_is_missing(self):
        with patch.object(email_service.settings, "RESEND_API_KEY", ""), patch(
            "app.services.email_service.resend.Emails.send"
        ) as mock_send:
            email_service.send_waitlist_confirmation_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
            )

            mock_send.assert_not_called()

    def test_should_set_api_key_before_send(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "confirm-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend") as mock_resend:
            email_service.send_waitlist_confirmation_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
            )

            assert mock_resend.api_key == "confirm-key"

    def test_should_html_escape_user_name_against_xss(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_confirmation_email(
                email="user@example.com",
                name="<b>injected</b>",
                event_title="Concert",
            )

            params = mock_send.call_args[0][0]
            assert "<b>injected</b>" not in params["html"]
            assert "&lt;b&gt;injected&lt;/b&gt;" in params["html"]

    def test_should_html_escape_event_title_against_xss(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_confirmation_email(
                email="user@example.com",
                name="Alice",
                event_title="<script>evil()</script>",
            )

            params = mock_send.call_args[0][0]
            assert "<script>" not in params["html"]

    def test_should_not_raise_when_resend_throws(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch(
            "app.services.email_service.resend.Emails.send",
            side_effect=Exception("network error"),
        ):
            # Must not raise
            email_service.send_waitlist_confirmation_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
            )

    def test_should_include_event_title_in_subject(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "noreply@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_confirmation_email(
                email="user@example.com",
                name="Alice",
                event_title="Summer Festival",
            )

            params = mock_send.call_args[0][0]
            assert "Summer Festival" in params["subject"]

    def test_should_log_warning_when_api_key_missing(self, caplog):
        with patch.object(email_service.settings, "RESEND_API_KEY", ""):
            with caplog.at_level("WARNING"):
                email_service.send_waitlist_confirmation_email(
                    email="user@example.com",
                    name="Alice",
                    event_title="Concert",
                )

            assert any(
                "RESEND_API_KEY not set" in rec.message for rec in caplog.records
            )

    def test_should_use_configured_from_email_as_sender(self):
        with patch.object(
            email_service.settings, "RESEND_API_KEY", "test-key"
        ), patch.object(
            email_service.settings, "RESEND_FROM_EMAIL", "custom@happin.test"
        ), patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_waitlist_confirmation_email(
                email="user@example.com",
                name="Alice",
                event_title="Concert",
            )

            params = mock_send.call_args[0][0]
            assert params["from"] == "custom@happin.test"
