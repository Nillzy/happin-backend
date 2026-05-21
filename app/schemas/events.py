"""Event-related Pydantic schemas."""

import re
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Literal, Optional
from datetime import datetime
from app.schemas.ticket_options import TicketOptionResponse
from app.schemas.custom_fields import CustomFieldResponse

_HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')


def _validate_hex_color(v: str | None) -> str | None:
    if v is not None and not _HEX_RE.match(v):
        raise ValueError("Farbe muss ein 6-stelliger Hex-Wert sein, z.B. #D4006B")
    return v


class LocationCreate(BaseModel):
    city: str | None = None
    street: str | None = None
    house_number: str | None = None
    postal_code: str | None = None
    country: str | None = None
    type: str | None = None
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("city")
    @classmethod
    def city_not_empty(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class EventCreate(BaseModel):
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    description: str | None = None
    category: str | None = None
    max_capacity: int | None = None
    max_tickets_per_person: int | None = 1
    is_public: bool
    is_free: bool = True
    location: LocationCreate
    status: str = "published"
    image_url: str | None = None
    gradient_id: int | None = None
    accent_color_primary: str | None = None
    accent_color_secondary: str | None = None
    location_is_private: bool = False

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        if len(v) > 255:
            raise ValueError("title must be at most 255 characters")
        return v

    @field_validator("max_capacity")
    @classmethod
    def capacity_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("max_capacity must be greater than 0")
        return v

    @field_validator("max_tickets_per_person")
    @classmethod
    def tickets_per_person_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("max_tickets_per_person must be greater than 0")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in ("draft", "published"):
            raise ValueError("status must be 'draft' or 'published'")
        return v

    @field_validator("accent_color_primary")
    @classmethod
    def validate_primary_color(cls, v: str | None) -> str | None:
        return _validate_hex_color(v)

    @field_validator("accent_color_secondary")
    @classmethod
    def validate_secondary_color(cls, v: str | None) -> str | None:
        return _validate_hex_color(v)


class LocationUpdate(BaseModel):
    city: str | None = None
    street: str | None = None
    house_number: str | None = None
    postal_code: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class EventUpdate(BaseModel):
    title: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    description: str | None = None
    category: str | None = None
    max_capacity: int | None = None
    max_tickets_per_person: int | None = None
    is_public: bool | None = None
    is_free: bool | None = None
    status: str | None = None
    location: LocationUpdate | None = None
    image_url: str | None = None
    gradient_id: int | None = None
    media_urls: list[str] | None = None
    location_is_private: bool | None = None
    accent_color_primary: str | None = None
    accent_color_secondary: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("title must not be empty")
            if len(v) > 255:
                raise ValueError("title must be at most 255 characters")
        return v

    @field_validator("max_capacity")
    @classmethod
    def capacity_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("max_capacity must be greater than 0")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in ("draft", "published"):
            raise ValueError("status must be 'draft' or 'published'")
        return v

    @field_validator("accent_color_primary")
    @classmethod
    def validate_update_primary_color(cls, v: str | None) -> str | None:
        return _validate_hex_color(v)

    @field_validator("accent_color_secondary")
    @classmethod
    def validate_update_secondary_color(cls, v: str | None) -> str | None:
        return _validate_hex_color(v)


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location_id: str
    city: str | None = None
    street: str | None = None
    house_number: str | None = None
    postal_code: str | None = None
    country: str | None = None
    type: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class EventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    description: str | None = None
    category: str | None = None
    max_capacity: int | None = None
    max_tickets_per_person: int | None = 1
    is_public: bool
    is_free: bool = True
    status: str = "published"
    image_url: str | None = None
    gradient_id: int | None = None
    location: LocationResponse | None = None
    participant_count: int = 0
    is_host: bool = False
    rsvp_accepted: int = 0
    rsvp_declined: int = 0
    waitlist_count: int = 0
    ticket_revenue_cents: int = 0
    is_deleted: bool = False
    deleted_at: datetime | None = None
    location_is_private: bool = False
    accent_color_primary: str | None = None
    accent_color_secondary: str | None = None


class EventListResponse(BaseModel):
    events: list[EventListItem]
    count: int


class EventDetailResponse(EventListItem):
    invitation_link: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    host_name: str | None = None
    media_urls: list[str] = []
    ticket_options: list[TicketOptionResponse] = []
    custom_fields: list[CustomFieldResponse] = []
    my_rsvp_status: Optional[str] = None
    ticket: list[dict] = []


class RsvpRequest(BaseModel):
    status: Literal['Accepted', 'Declined', 'Pending']
    ticket_count: int = 1
    guest_names: list[str] | None = None


class RsvpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_participation_id: str
    event_id: str
    person_id: str
    status: str
