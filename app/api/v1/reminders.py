"""Reminder-Endpoints (Anforderung K4): Präferenzen + Web-Push-Subscriptions."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.core.auth import get_current_user
from app.core.config import settings
from app.schemas.reminder import (
    ExpoPushTokenCreate,
    ExpoPushTokenDelete,
    ExpoPushTokenItem,
    ExpoPushTokenListResponse,
    ReminderPreferenceResponse,
    ReminderPreferenceUpdate,
    VapidPublicKeyResponse,
    WebPushSubscriptionCreate,
    WebPushSubscriptionDelete,
    WebPushSubscriptionItem,
    WebPushSubscriptionListResponse,
)
from app.services import expo_push_service, person_service, reminder_service

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


@router.post(
    "/me/expo-push-tokens",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def register_expo_push_token(
    body: ExpoPushTokenCreate,
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    """Native iOS/Android: Expo-Push-Token registrieren."""
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    expo_push_service.upsert_token(
        person_id=person["person_id"],
        token=body.token,
        platform=body.platform,
        user_agent=body.user_agent,
        auth_token=token,
    )


@router.delete(
    "/me/expo-push-tokens",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_expo_push_token(
    body: ExpoPushTokenDelete,
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    expo_push_service.delete_token(person["person_id"], body.token, token)


# ── Geräte-Verwaltung ────────────────────────────────────────────────


@router.get(
    "/me/web-push-subscriptions",
    response_model=WebPushSubscriptionListResponse,
)
async def list_my_web_push_subscriptions(
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    """Liefert alle Web-Push-Subscriptions des Users (für Geräte-Verwaltung)."""
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    rows = reminder_service.list_subscriptions(person["person_id"], token)
    return WebPushSubscriptionListResponse(
        items=[WebPushSubscriptionItem(**r) for r in rows]
    )


@router.delete(
    "/me/web-push-subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_my_web_push_subscription(
    subscription_id: str,
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    ok = reminder_service.delete_subscription_by_id(
        person["person_id"], token, subscription_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="subscription_not_found")


@router.get(
    "/me/expo-push-tokens",
    response_model=ExpoPushTokenListResponse,
)
async def list_my_expo_push_tokens(
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    """Liefert alle Expo-Push-Tokens des Users (für Geräte-Verwaltung)."""
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    rows = expo_push_service.list_tokens(person["person_id"], token)
    return ExpoPushTokenListResponse(items=[ExpoPushTokenItem(**r) for r in rows])


@router.delete(
    "/me/expo-push-tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_my_expo_push_token(
    token_id: str,
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    ok = expo_push_service.delete_token_by_id(person["person_id"], token_id, token)
    if not ok:
        raise HTTPException(status_code=404, detail="token_not_found")
