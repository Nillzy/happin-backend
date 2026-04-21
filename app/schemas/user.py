"""User-related Pydantic schemas."""

from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    """User information response."""

    id: str
    phone: str | None = None
    email: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
