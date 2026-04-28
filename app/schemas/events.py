"""Event-related Pydantic schemas."""

from pydantic import BaseModel
from datetime import datetime


class LocationResponse(BaseModel):
    location_id: int
    city: str
    street: str | None = None
    house_number: str | None = None
    postal_code: str | None = None
    country: str | None = None
    type: str | None = None

    class Config:
        from_attributes = True


class EventListItem(BaseModel):
    event_id: int
    title: str
    date: datetime
    description: str | None = None
    category: str | None = None
    max_capacity: float | None = None
    is_public: bool
    image_url: str | None = None
    location: LocationResponse | None = None
    participant_count: int = 0

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    events: list[EventListItem]
    count: int


class EventDetailResponse(EventListItem):
    invitation_link: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    host_name: str | None = None
    media_urls: list[str] = []
