"""Notification-Endpoints: In-App-Liste, Unread-Count, Mark-Read."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.core.auth import get_current_user
from app.schemas.notification import (
    MarkAllReadResponse,
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse,
)
from app.services import notification_service, person_service

router = APIRouter()
_bearer = HTTPBearer()


def _token(credentials=Depends(_bearer)) -> str:
    return credentials.credentials


@router.get("/me/notifications", response_model=NotificationListResponse)
async def list_my_notifications(
    limit: int = 20,
    before: str | None = None,
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    rows = notification_service.list_for_person(person["person_id"], token, limit=limit, before_id=before)
    return NotificationListResponse(items=[NotificationItem(**r) for r in rows])


@router.get("/me/notifications/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    return UnreadCountResponse(count=notification_service.unread_count(person["person_id"], token))


@router.post("/me/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_one_read(
    notification_id: str,
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    ok = notification_service.mark_read(notification_id, person["person_id"], token)
    if not ok:
        raise HTTPException(status_code=404, detail="notification_not_found_or_already_read")


@router.post("/me/notifications/read-all", response_model=MarkAllReadResponse)
async def mark_all_read(
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    return MarkAllReadResponse(marked=notification_service.mark_all_read(person["person_id"], token))


@router.post("/me/notifications/test")
async def send_test_notification(
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    """Erzeugt eine Test-Benachrichtigung für den aktuellen User (In-App + Web-Push)."""
    person = person_service.get_or_create_person(user.user.id, user.user.email, token)
    pushed = notification_service.send_test_notification(person["person_id"])
    return {"ok": True, "pushed": pushed}
