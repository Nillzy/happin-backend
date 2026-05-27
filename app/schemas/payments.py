"""Payment-related Pydantic schemas."""

from pydantic import BaseModel, Field


class CreateCheckoutSessionRequest(BaseModel):
    ticket_option_id: str
    quantity: int = Field(ge=1, le=99, default=1)


class CreateCheckoutSessionResponse(BaseModel):
    checkout_url: str
    ticket_order_id: str


class CheckoutOrderStatusResponse(BaseModel):
    order_status: str
    fulfilled: bool
    event_id: str
    ticket_order_id: str


class ConnectOnboardingResponse(BaseModel):
    url: str
    account_id: str


class ConnectStatusResponse(BaseModel):
    has_account: bool = False
    charges_enabled: bool = False
    payouts_enabled: bool = False
    onboarding_complete: bool = False


class DashboardLinkResponse(BaseModel):
    url: str


class PaymentSummaryResponse(BaseModel):
    gross_cents: int = 0
    platform_fee_cents: int = 0
    net_cents: int = 0
    paid_orders: int = 0


class PayoutRequest(BaseModel):
    pass


class PayoutResponse(BaseModel):
    payout_id: str
    amount_cents: int
    currency: str = "eur"
