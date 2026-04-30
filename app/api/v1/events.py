"""Event endpoints for listing, viewing, and creating events."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.auth import get_current_user, get_current_user_optional
from app.schemas.events import EventCreate, EventUpdate, EventListItem, EventListResponse, EventDetailResponse
from app.schemas.ticket_options import TicketOptionResponse
from app.schemas.participants import (
    ParticipantListResponse,
    ParticipantResponse,
    PersonInfo,
    ParticipantCounts,
    RemoveParticipantsRequest,
    RemoveParticipantsResponse,
)
from app.services import event_service
from app.services import person_service

router = APIRouter()
logger = logging.getLogger(__name__)

optional_bearer = HTTPBearer(auto_error=False)


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
        is_free=raw.get("is_free", True),
        status=raw.get("status", "published"),
        image_url=image_url,
        location=raw.get("location"),
        participant_count=participant_count,
        is_host=raw.get("is_host", False),
    )


@router.get("/", response_model=EventListResponse)
async def list_public_events(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user_optional),
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
):
    """List all public events with pagination."""
    person_id = None
    if user and credentials:
        person = person_service.get_or_create_person(
            supabase_user_id=user.user.id,
            email=user.user.email,
            token=credentials.credentials,
        )
        person_id = person["person_id"]

    raw_events = event_service.get_public_events(limit=limit, offset=offset, person_id=person_id)
    events = [_to_list_item(e) for e in raw_events]
    return EventListResponse(events=events, count=len(events))


def _to_detail(raw: dict) -> EventDetailResponse:
    media = raw.get("event_media") or []
    media_urls = [m["media_url"] for m in media]
    image_url = media_urls[0] if media_urls else None

    participations = raw.get("event_participation") or []
    participant_count = len(participations)

    hosts = raw.get("event_host") or []
    host_name = None
    if hosts:
        person = hosts[0].get("person") or {}
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
        is_free=raw.get("is_free", True),
        status=raw.get("status", "published"),
        image_url=image_url,
        location=raw.get("location"),
        participant_count=participant_count,
        invitation_link=raw.get("invitation_link"),
        created_at=raw.get("created_at"),
        updated_at=raw.get("updated_at"),
        host_name=host_name,
        media_urls=media_urls,
        ticket_options=[
            TicketOptionResponse(**opt)
            for opt in (raw.get("ticket_option") or [])
        ],
    )


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event_detail(
    event_id: str,
    user=Depends(get_current_user_optional),
):
    raw = event_service.get_event_by_id(event_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Event not found")

    if raw.get("status") == "draft":
        if not user:
            raise HTTPException(status_code=404, detail="Event not found")
        hosts = raw.get("event_host") or []
        is_host = any(
            h.get("person", {}).get("supabase_user_id") == user.user.id
            for h in hosts
        )
        if not is_host:
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


@router.patch("/{event_id}", response_model=EventDetailResponse)
async def update_event_endpoint(
    event_id: str,
    body: EventUpdate,
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

        update_data = body.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        raw = event_service.update_event(event_id, update_data, person_id, credentials.credentials)
        if not raw:
            raise HTTPException(status_code=403, detail="Not authorized to update this event")

        return _to_detail(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Event update error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{event_id}/participants", response_model=ParticipantListResponse)
async def get_participants(
    event_id: str,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Get all participants for an event. Only accessible by the host."""
    # Check event exists first
    event = event_service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=credentials.credentials,
    )
    person_id = person["person_id"]

    if not event_service.is_user_host(event_id=event_id, person_id=person_id):
        raise HTTPException(status_code=403, detail="Only the host can view participants")

    data = event_service.get_event_participants(event_id=event_id)

    participants = [
        ParticipantResponse(
            participation_id=p["event_participation_id"],
            person=PersonInfo(
                person_id=p["person"]["person_id"],
                first_name=p["person"]["first_name"],
                last_name=p["person"].get("last_name"),
                phone_number=p["person"].get("phone_number"),
            ),
            status=p["status"],
            created_at=p.get("created_at"),
        )
        for p in data["participants"]
    ]

    return ParticipantListResponse(
        participants=participants,
        counts=ParticipantCounts(**data["counts"]),
    )


@router.delete("/{event_id}/participants", response_model=RemoveParticipantsResponse)
async def delete_participants(
    event_id: str,
    request: RemoveParticipantsRequest,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Remove participants from an event. Only accessible by the host."""
    # Check event exists first
    event = event_service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=credentials.credentials,
    )
    person_id = person["person_id"]

    if not event_service.is_user_host(event_id=event_id, person_id=person_id):
        raise HTTPException(status_code=403, detail="Only the host can remove participants")

    removed_count = event_service.remove_participants(
        event_id=event_id,
        participation_ids=request.participation_ids,
        token=credentials.credentials,
    )

    return RemoveParticipantsResponse(removed_count=removed_count)
