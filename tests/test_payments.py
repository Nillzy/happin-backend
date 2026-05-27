"""Tests for Stripe Connect payment flows."""

from unittest.mock import MagicMock, patch
import pytest


class TestPaymentServiceFeeCalculation:
    """Test application fee calculation."""

    def test_fee_5_percent_default(self):
        """5% (500 BPS) of 10€ = 0.50€."""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.PLATFORM_FEE_BPS = 500
            from app.services.payment_service import calculate_application_fee
            assert calculate_application_fee(1000) == 50

    def test_fee_10_percent(self):
        """10% (1000 BPS) of 79€ = 7.90€."""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.PLATFORM_FEE_BPS = 1000
            from app.services.payment_service import calculate_application_fee
            assert calculate_application_fee(7900) == 790

    def test_fee_rounds_down(self):
        """Rounding: 5% of 999 = 49.95 → 50."""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.PLATFORM_FEE_BPS = 500
            from app.services.payment_service import calculate_application_fee
            assert calculate_application_fee(999) == 50

    def test_fee_zero_amount(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.PLATFORM_FEE_BPS = 500
            from app.services.payment_service import calculate_application_fee
            assert calculate_application_fee(0) == 0


class TestFulfillmentIdempotency:
    """Test that fulfillment is idempotent."""

    @patch("app.services.payment_service.get_supabase")
    def test_already_paid_order_returns_true(self, mock_get_supabase):
        """If order is already paid with tickets, fulfill is a successful no-op (idempotent)."""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        order_data = {
            "ticket_order_id": "order-1",
            "status": "paid",
            "event_id": "e1",
            "person_id": "p1",
            "quantity": 1,
            "ticket_option_id": None,
        }

        def table_side_effect(name):
            t = MagicMock()
            if name == "ticket_order":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data=order_data
                )
            elif name == "ticket":
                t.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[{"ticket_id": "t1"}]
                )
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services.payment_service import fulfill_ticket_order
        result = fulfill_ticket_order("order-1")
        assert result is True


class TestCancelTicketOrder:
    @patch("app.services.payment_service.stripe_payment.create_refund")
    @patch("app.services.payment_service._resolve_payment_intent_id", return_value=None)
    @patch("app.services.payment_service.get_supabase")
    def test_cancel_without_payment_intent_raises(
        self, mock_get_supabase, _mock_resolve_pi, _mock_refund
    ):
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb
        paid = MagicMock()
        paid.data = [{
            "ticket_order_id": "order-1",
            "amount_total_cents": 1000,
            "ticket_option_id": None,
            "quantity": 1,
        }]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = paid

        from app.services.payment_service import cancel_ticket_order

        with pytest.raises(ValueError, match="refund_not_possible"):
            cancel_ticket_order("e1", "p1")


class TestAbandonCheckout:
    @patch("app.services.payment_service.stripe_payment.expire_checkout_session")
    @patch("app.services.payment_service.stripe_payment.retrieve_checkout_session")
    @patch("app.services.payment_service.get_supabase")
    def test_abandon_expires_open_session(
        self, mock_get_supabase, mock_retrieve, mock_expire
    ):
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb
        pending = MagicMock()
        pending.data = [{
            "ticket_order_id": "order-1",
            "event_id": "event-a",
            "stripe_checkout_session_id": "cs_test_1",
        }]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = pending
        mock_retrieve.return_value = MagicMock(status="open")

        from app.services.payment_service import abandon_checkout

        assert abandon_checkout(event_id="event-a", person_id="p1") is True
        mock_expire.assert_called_once_with("cs_test_1")


class TestCreateCheckoutSession:
    @patch("app.services.payment_service.abandon_checkout")
    @patch("app.services.payment_service.sync_pending_checkouts")
    @patch("app.services.payment_service.booking_service.expire_stale_pending_orders")
    @patch("app.services.payment_service.get_host_stripe_account")
    @patch("app.services.payment_service.get_supabase")
    def test_create_checkout_abandons_existing_session(
        self,
        mock_get_supabase,
        mock_host,
        _mock_expire_stale,
        _mock_sync,
        mock_abandon,
    ):
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb
        mock_host.return_value = {
            "stripe_connect_account_id": "acct_1",
            "stripe_connect_charges_enabled": True,
        }
        mock_abandon.return_value = True

        with patch(
            "app.services.payment_service.booking_service.validate_booking",
            side_effect=ValueError("ticket_option_wrong_event"),
        ):
            from app.services.payment_service import create_checkout_session

            with pytest.raises(ValueError, match="ticket_option_wrong_event"):
                create_checkout_session(
                    event_id="event-a",
                    person_id="p1",
                    ticket_option_id="opt-1",
                    quantity=1,
                )

        mock_abandon.assert_called_once_with(event_id="event-a", person_id="p1")


class TestCheckoutValidation:
    @patch("app.services.payment_service.get_host_stripe_account")
    @patch("app.services.payment_service.get_supabase")
    def test_ticket_option_wrong_event_raises(self, mock_get_supabase, mock_host):
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb
        mock_host.return_value = {
            "stripe_connect_account_id": "acct_1",
            "stripe_connect_charges_enabled": True,
        }

        option_result = MagicMock()
        option_result.data = {
            "name": "VIP",
            "price": "10.00",
            "quantity_limit": 100,
            "event_id": "other-event",
        }

        event_result = MagicMock()
        event_result.data = {"max_capacity": None, "cancelled_at": None}

        def table_side_effect(table_name):
            tbl = MagicMock()
            if table_name == "event":
                tbl.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = event_result
            tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = option_result
            return tbl

        mock_sb.table.side_effect = table_side_effect

        from app.services.payment_service import create_checkout_session

        with pytest.raises(ValueError, match="ticket_option_wrong_event"):
            create_checkout_session(
                event_id="event-a",
                person_id="p1",
                ticket_option_id="opt-1",
                quantity=1,
            )


class TestTicketGuard:
    """Test that paid tickets are rejected via direct booking."""

    @patch("app.api.v1.tickets.booking_service.validate_booking", side_effect=ValueError("payment_required"))
    @patch("app.api.v1.tickets.get_supabase_for_user")
    @patch("app.core.auth.get_current_user")
    @patch("app.services.person_service.get_or_create_person")
    def test_paid_option_rejected(self, mock_person, mock_auth, mock_supabase_for_user, _mock_validate, client):
        """POST /events/{id}/tickets with paid option returns 400."""
        mock_auth.return_value = MagicMock(user=MagicMock(id="uid-1", email="test@test.com"))
        mock_person.return_value = {"person_id": "p1", "first_name": "Test", "last_name": "User"}

        mock_sb = MagicMock()
        mock_supabase_for_user.return_value = mock_sb

        # event exists
        event_result = MagicMock()
        event_result.data = {"max_capacity": 100}

        # ticket_option has price > 0
        option_result = MagicMock()
        option_result.data = {"price": "15.00"}

        def table_side_effect(name):
            t = MagicMock()
            if name == "event":
                t.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = event_result
            elif name == "ticket_option":
                t.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = option_result
            return t

        mock_sb.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/events/event-123/tickets",
            json={"ticket_option_id": "opt-paid", "quantity": 1},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert response.status_code == 400
        assert "checkout" in response.json()["detail"].lower()


class TestWebhookSignatureVerification:
    """Test webhook signature validation."""

    def test_invalid_signature_returns_400(self, client):
        """Webhook with bad signature should return 400."""
        response = client.post(
            "/api/v1/webhooks/stripe",
            content=b'{"type": "checkout.session.completed"}',
            headers={"stripe-signature": "bad_sig", "Content-Type": "application/json"},
        )
        assert response.status_code == 400


class TestPayoutGuard:
    """Test payout guards (event not ended, no balance)."""

    @patch("app.core.auth.get_current_user")
    @patch("app.services.person_service.get_or_create_person")
    @patch("app.api.v1.payments.get_supabase_admin")
    def test_payout_before_event_returns_400(self, mock_get_supabase, mock_person, mock_auth, client):
        """Payout before event ends returns 400."""
        mock_auth.return_value = MagicMock(user=MagicMock(id="uid-1", email="test@test.com"))
        mock_person.return_value = {"person_id": "p1"}

        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        # Host check passes
        host_result = MagicMock()
        host_result.data = {"event_host_id": "eh1"}

        # Event in the future
        event_result = MagicMock()
        event_result.data = {"starts_at": "2099-12-31T23:59:59+00:00"}

        tables_called = []

        def table_side_effect(name):
            tables_called.append(name)
            t = MagicMock()
            if name == "event_host":
                t.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = host_result
            elif name == "event":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = event_result
            return t

        mock_sb.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/events/event-123/payout",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert response.status_code == 400
        assert "not ended" in response.json()["detail"].lower()
