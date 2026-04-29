"""Event-related Pydantic schemas."""

from pydantic import BaseModel, field_validator
from datetime import datetime


class LocationCreate(BaseModel):
    city: str
    street: str | None = None
    house_number: str | None = None
    postal_code: str | None = None
    country: str | None = None
    type: str | None = None
    description: str | None = None

    @field_validator("city")
    @classmethod
    def city_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("city must not be empty")
        return v.strip()


class EventCreate(BaseModel):
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    description: str | None = None
    category: str | None = None
    max_capacity: int | None = None
    is_public: bool
    location: LocationCreate

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        if len(v) > 255:
            raise ValueError("title must be at most 255 characters")
        return v

    @field_validator("starts_at")
    @classmethod
    def starts_at_in_future(cls, v: datetime) -> datetime:
        if v <= datetime.now():
            raise ValueError("starts_at must be in the future")
        return v

    @field_validator("max_capacity")
    @classmethod
    def capacity_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("max_capacity must be greater than 0")
        return v


class LocationResponse(BaseModel):
    location_id: str
    city: str
    street: str | None = None
    house_number: str | None = None
    postal_code: str | None = None
    country: str | None = None
    type: str | None = None

    class Config:
        from_attributes = True


class EventListItem(BaseModel):
    event_id: str
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    description: str | None = None
    category: str | None = None
    max_capacity: int | None = None
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
