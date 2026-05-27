"""Reminder-related Pydantic schemas (Anforderung K4)."""

from datetime import datetime

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


class ExpoPushTokenCreate(BaseModel):
    token: str
    platform: str = Field(pattern="^(ios|android)$")
    user_agent: str | None = None


class ExpoPushTokenDelete(BaseModel):
    token: str


# ── Geräte-Verwaltung ────────────────────────────────────────────────


class WebPushSubscriptionItem(BaseModel):
    web_push_subscription_id: str
    endpoint: str
    user_agent: str | None = None
    created_at: datetime


class WebPushSubscriptionListResponse(BaseModel):
    items: list[WebPushSubscriptionItem]


class ExpoPushTokenItem(BaseModel):
    expo_push_token_id: str
    platform: str
    user_agent: str | None = None
    created_at: datetime


class ExpoPushTokenListResponse(BaseModel):
    items: list[ExpoPushTokenItem]
