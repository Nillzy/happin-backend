"""Reminder-Endpoints (Anforderung K4): Präferenzen + Web-Push-Subscriptions."""

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer

from app.core.auth import get_current_user
from app.core.config import settings
from app.schemas.reminder import (
    ReminderPreferenceResponse,
    ReminderPreferenceUpdate,
    VapidPublicKeyResponse,
    WebPushSubscriptionCreate,
    WebPushSubscriptionDelete,
)
from app.services import person_service, reminder_service

router = APIRouter()
_bearer = HTTPBearer()


def _token(credentials=Depends(_bearer)) -> str:
    return credentials.credentials


@router.get("/me/reminder-preferences", response_model=ReminderPreferenceResponse)
async def get_reminder_preferences(
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    pref = reminder_service.get_preference(person["person_id"], token)
    return ReminderPreferenceResponse(**pref)


@router.patch("/me/reminder-preferences", response_model=ReminderPreferenceResponse)
async def update_reminder_preferences(
    body: ReminderPreferenceUpdate,
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    pref = reminder_service.upsert_preference(
        person["person_id"], token, body.enabled, body.lead_time_minutes
    )
    return ReminderPreferenceResponse(**pref)


@router.post(
    "/me/web-push-subscriptions",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def register_web_push_subscription(
    body: WebPushSubscriptionCreate,
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    reminder_service.upsert_subscription(
        person["person_id"],
        token,
        endpoint=body.endpoint,
        p256dh=body.keys.p256dh,
        auth=body.keys.auth,
        user_agent=body.user_agent,
    )


@router.delete(
    "/me/web-push-subscriptions",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_web_push_subscription(
    body: WebPushSubscriptionDelete,
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    reminder_service.delete_subscription(person["person_id"], token, body.endpoint)


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key():
    """Public-Key für Web-Push-Subscriptions im Browser. Kein Auth nötig."""
    return VapidPublicKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)
