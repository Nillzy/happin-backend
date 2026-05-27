"""Tests for persistent Stripe webhook inbox."""

from unittest.mock import MagicMock, patch

from app.services.stripe_webhook_service import persist_webhook_event


class TestPersistWebhookEvent:
    @patch("app.services.stripe_webhook_service.get_supabase_admin")
    def test_persist_when_maybe_single_returns_none(self, mock_get_supabase):
        """Supabase SDK returns None (not empty response) when no row exists."""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        select_chain = mock_sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value
        select_chain.execute.return_value = None

        insert_chain = mock_sb.table.return_value.insert.return_value
        insert_chain.execute.return_value = MagicMock(
            data=[{
                "webhook_event_id": "wh-1",
                "stripe_event_id": "evt_123",
                "event_type": "checkout.session.completed",
                "status": "pending",
            }]
        )

        record = persist_webhook_event(
            stripe_event_id="evt_123",
            event_type="checkout.session.completed",
            payload={"id": "evt_123", "type": "checkout.session.completed"},
        )

        assert record["stripe_event_id"] == "evt_123"
        assert record["status"] == "pending"
        insert_chain.execute.assert_called_once()
