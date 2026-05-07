"""Ticket-related Pydantic schemas for the tickets endpoint."""

from pydantic import BaseModel, Field


class CreateTicketsRequest(BaseModel):
    ticket_option_id: str | None = None
    quantity: int = Field(ge=1, le=10, default=1)


class CreateTicketsResponse(BaseModel):
    tickets: list[dict]


class ScanTicketRequest(BaseModel):
    qr_token: str


class ScanTicketResponse(BaseModel):
    valid: bool
    reason: str | None = None
    guest_name: str | None = None
    used_at: str | None = None
    ticket_number: int | None = None
    option_name: str | None = None
