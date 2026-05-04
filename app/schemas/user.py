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
    event_id: str
    event_title: str
    ticket_option_name: str
    price: float
    currency: str
    status: str
    purchased_at: datetime | None = None


class TicketListResponse(BaseModel):
    tickets: list[TicketItem]
    total: int
