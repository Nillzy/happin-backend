"""Event endpoints for listing and viewing public events."""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import get_current_user_optional
from app.schemas.events import EventListItem, EventListResponse, EventDetailResponse
from app.services import event_service

router = APIRouter()


def _to_list_item(raw: dict) -> EventListItem:
    media = raw.get("event_media") or []
    image_url = media[0]["media_url"] if media else None

    participations = raw.get("event_participation") or []
    participant_count = len(participations)

    return EventListItem(
        event_id=raw["event_id"],
        title=raw["title"],
        date=raw["date"],
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


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event_detail(
    event_id: int,
    user=Depends(get_current_user_optional),
):
    raw = event_service.get_event_by_id(event_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Event not found")

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
        date=raw["date"],
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
