"""Event endpoints for listing, viewing, and creating events."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from app.core.auth import get_current_user, get_current_user_optional
from app.schemas.events import EventCreate, EventListItem, EventListResponse, EventDetailResponse
from app.services import event_service
from app.services import person_service

router = APIRouter()
logger = logging.getLogger(__name__)


def _to_list_item(raw: dict) -> EventListItem:
    media = raw.get("event_media") or []
    image_url = media[0]["media_url"] if media else None

    participations = raw.get("event_participation") or []
    participant_count = len(participations)

    return EventListItem(
        event_id=raw["event_id"],
        title=raw["title"],
        starts_at=raw["starts_at"],
        ends_at=raw.get("ends_at"),
        description=raw.get("description"),
        category=raw.get("category"),
        max_capacity=raw.get("max_capacity"),
        is_public=raw["is_public"],
        image_url=image_url,
        location=raw.get("location"),
        participant_count=participant_count,
    )


@router.get("/", response_model=EventListResponse)
async def list_public_events(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user_optional),
):
    raw_events = event_service.get_public_events(limit=limit, offset=offset)
    events = [_to_list_item(e) for e in raw_events]
    return EventListResponse(events=events, count=len(events))


def _to_detail(raw: dict) -> EventDetailResponse:
    media = raw.get("event_media") or []
    media_urls = [m["media_url"] for m in media]
    image_url = media_urls[0] if media_urls else None

    participations = raw.get("event_participation") or []
    participant_count = len(participations)

    host = next(
        (p for p in participations if p.get("role") == "Host"),
        None,
    )
    host_name = None
    if host and host.get("person"):
        person = host["person"]
        parts = [person.get("first_name", ""), person.get("last_name", "")]
        host_name = " ".join(p for p in parts if p).strip() or None

    return EventDetailResponse(
        event_id=raw["event_id"],
        title=raw["title"],
        starts_at=raw["starts_at"],
        ends_at=raw.get("ends_at"),
        description=raw.get("description"),
        category=raw.get("category"),
        max_capacity=raw.get("max_capacity"),
        is_public=raw["is_public"],
        image_url=image_url,
        location=raw.get("location"),
        participant_count=participant_count,
        invitation_link=raw.get("invitation_link"),
        created_at=raw.get("created_at"),
        updated_at=raw.get("updated_at"),
        host_name=host_name,
        media_urls=media_urls,
    )


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event_detail(
    event_id: str,
    user=Depends(get_current_user_optional),
):
    raw = event_service.get_event_by_id(event_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Event not found")

    return _to_detail(raw)


@router.post("/", response_model=EventDetailResponse, status_code=201)
async def create_event(
    body: EventCreate,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    try:
        person = person_service.get_or_create_person(
            supabase_user_id=user.user.id,
            email=user.user.email,
            token=credentials.credentials,
        )
        person_id = person["person_id"]

        raw = event_service.create_event(body.model_dump(), person_id, credentials.credentials)
        if not raw:
            raise HTTPException(status_code=500, detail="Event creation failed")

        return _to_detail(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Event creation error")
        raise HTTPException(status_code=500, detail=str(e))
