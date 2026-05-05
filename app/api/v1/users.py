"""User account endpoints — stats, events, tickets, account deletion."""

from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.supabase import get_supabase, get_supabase_for_user
from app.schemas.user import UserStatsResponse, TicketListResponse
from app.schemas.events import EventListResponse, EventListItem, LocationResponse
from app.services import person_service, user_service

router = APIRouter()
_bearer = HTTPBearer()


def _token(credentials=Depends(_bearer)) -> str:
    return credentials.credentials


def _build_event_list(raw: list[dict]) -> EventListResponse:
    items = []
    for e in raw:
        loc_data = e.get("location")
        location = LocationResponse(**loc_data) if loc_data else None
        media = e.get("event_media") or []
        image_url = media[0]["media_url"] if media else None
        parts = e.get("event_participation") or []
        items.append(EventListItem(
            event_id=e["event_id"],
            title=e["title"],
            starts_at=e["starts_at"],
            ends_at=e.get("ends_at"),
            description=e.get("description"),
            category=e.get("category"),
            max_capacity=e.get("max_capacity"),
            is_public=e["is_public"],
            is_free=e.get("is_free", True),
            status=e.get("status", "published"),
            image_url=image_url,
            location=location,
            participant_count=len(parts),
            is_host=e.get("is_host", False),
        ))
    return EventListResponse(events=items, count=len(items))


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_user_stats(user=Depends(get_current_user), token: str = Depends(_token)):
    supabase_user_id = user.user.id
    email = user.user.email
    person = person_service.get_or_create_person(supabase_user_id, email, token)
    stats = user_service.get_user_stats(person["person_id"])
    return UserStatsResponse(**stats)


@router.get("/me/events", response_model=EventListResponse)
async def get_user_events(
    role: Optional[Literal["organizer", "attendee"]] = Query(None),
    period: Literal["upcoming", "past"] = Query("upcoming"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_user),
    token: str = Depends(_token),
):
    supabase_user_id = user.user.id
    email = user.user.email
    person = person_service.get_or_create_person(supabase_user_id, email, token)
    raw = user_service.get_user_events(
        person_id=person["person_id"],
        role=role,
        period=period,
        limit=limit,
        offset=offset,
    )
    return _build_event_list(raw)


@router.get("/me/tickets", response_model=TicketListResponse)
async def get_user_tickets(user=Depends(get_current_user), token: str = Depends(_token)):
    supabase_user_id = user.user.id
    email = user.user.email
    person = person_service.get_or_create_person(supabase_user_id, email, token)
    result = user_service.get_user_tickets(person["person_id"])
    return TicketListResponse(**result)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(user=Depends(get_current_user), token: str = Depends(_token)):
    supabase_user_id = user.user.id
    try:
        user_service.delete_user(supabase_user_id, token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account deletion failed: {str(e)}",
        )


class UpdateNameRequest(BaseModel):
    first_name: str
    last_name: str


@router.patch("/me/name", status_code=status.HTTP_200_OK)
async def update_name(body: UpdateNameRequest, user=Depends(get_current_user), token: str = Depends(_token)):
    """Update first_name and last_name in the person table."""
    supabase_user_id = user.user.id
    email = user.user.email
    person = person_service.get_or_create_person(supabase_user_id, email, token)
    sb = get_supabase_for_user(token)
    sb.table("person").update({
        "first_name": body.first_name,
        "last_name": body.last_name if body.last_name else None,
    }).eq("person_id", person["person_id"]).execute()
    return {"first_name": body.first_name, "last_name": body.last_name}


class UpdateCityRequest(BaseModel):
    city: str


@router.patch("/me/city", status_code=status.HTTP_200_OK)
async def update_city(body: UpdateCityRequest, user=Depends(get_current_user), token: str = Depends(_token)):
    """Update city in the person table."""
    supabase_user_id = user.user.id
    email = user.user.email
    person = person_service.get_or_create_person(supabase_user_id, email, token)
    sb = get_supabase_for_user(token)
    sb.table("person").update({
        "city": body.city if body.city else None,
    }).eq("person_id", person["person_id"]).execute()
    return {"city": body.city}
