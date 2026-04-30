"""User-related Pydantic schemas."""

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone: str | None = None
    email: str | None = None
    created_at: datetime | None = None
