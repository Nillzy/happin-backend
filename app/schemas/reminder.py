"""Reminder-related Pydantic schemas (Anforderung K4)."""

from pydantic import BaseModel, Field


class ReminderPreferenceResponse(BaseModel):
    enabled: bool
    lead_time_minutes: int


class ReminderPreferenceUpdate(BaseModel):
    enabled: bool | None = None
    lead_time_minutes: int | None = Field(default=None, ge=1, le=10080)


class WebPushKeys(BaseModel):
    p256dh: str
    auth: str


class WebPushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: WebPushKeys
    user_agent: str | None = None


class WebPushSubscriptionDelete(BaseModel):
    endpoint: str


class VapidPublicKeyResponse(BaseModel):
    public_key: str | None
