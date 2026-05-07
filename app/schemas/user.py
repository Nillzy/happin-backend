"""User-related Pydantic schemas."""

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone: str | None = None
    email: str | None = None
    created_at: datetime | None = None


class UserStatsResponse(BaseModel):
    events_attended: int
    events_created: int
    tickets_total: int
    participants_total: int


class TicketItem(BaseModel):
    ticket_id: str
    qr_token: str
    event_id: str
    event_title: str
    starts_at: datetime | None = None
    city: str | None = None
    ticket_option_name: str
    price: float
    currency: str
    status: str
    created_at: datetime | None = None
    used_at: datetime | None = None


class TicketListResponse(BaseModel):
    tickets: list[TicketItem]
    total: int
