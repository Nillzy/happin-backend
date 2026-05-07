"""User account endpoints — stats, events, tickets, account deletion."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.supabase import get_supabase_for_user
from app.schemas.user import UserStatsResponse, TicketListResponse
from app.services import person_service, user_service

router = APIRouter()
_bearer = HTTPBearer()


def _token(credentials=Depends(_bearer)) -> str:
    return credentials.credentials


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_user_stats(user=Depends(get_current_user), token: str = Depends(_token)):
    supabase_user_id = user.user.id
    email = user.user.email
    person = person_service.get_or_create_person(supabase_user_id, email, token)
    stats = user_service.get_user_stats(person["person_id"])
    return UserStatsResponse(**stats)


@router.get("/me/tickets", response_model=TicketListResponse)
async def get_user_tickets(user=Depends(get_current_user), token: str = Depends(_token)):
    supabase_user_id = user.user.id
    email = user.user.email
    person = person_service.get_or_create_person(supabase_user_id, email, token)
    result = user_service.get_user_tickets(person["person_id"], token)
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


@router.get("/me/profile", status_code=status.HTTP_200_OK)
async def get_profile(user=Depends(get_current_user), token: str = Depends(_token)):
    """Get basic profile info including city."""
    supabase_user_id = user.user.id
    email = user.user.email
    person = person_service.get_or_create_person(supabase_user_id, email, token)
    return {
        "city": person.get("city") or "",
        "first_name": person.get("first_name") or "",
        "last_name": person.get("last_name") or "",
    }


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
