"""Ticket option schemas for pricing categories."""

from pydantic import BaseModel, field_validator


class TicketOptionItem(BaseModel):
    ticket_option_id: str | None = None
    name: str
    description: str | None = None
    price: float = 0.0
    quantity_limit: int | None = None
    sort_order: int = 0

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        if len(v) > 100:
            raise ValueError("name must be at most 100 characters")
        return v

    @field_validator("price")
    @classmethod
    def price_not_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price must be >= 0")
        return v

    @field_validator("quantity_limit")
    @classmethod
    def quantity_limit_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("quantity_limit must be > 0")
        return v


class TicketOptionResponse(BaseModel):
    ticket_option_id: str
    name: str
    description: str | None = None
    price: float
    quantity_limit: int | None = None
    sort_order: int = 0


class TicketOptionSyncRequest(BaseModel):
    ticket_options: list[TicketOptionItem]
