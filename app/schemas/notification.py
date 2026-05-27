"""Notification-Schemas (In-App-Benachrichtigungen)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NotificationItem(BaseModel):
    notification_id: str
    event_id: str | None = None
    type: str
    payload: dict[str, Any] = {}
    created_at: datetime
    read_at: datetime | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]


class UnreadCountResponse(BaseModel):
    count: int


class MarkAllReadResponse(BaseModel):
    marked: int
