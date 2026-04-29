"""Ticket option endpoints — UPSERT sync for event pricing categories."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer

from app.core.auth import get_current_user
from app.core.supabase import get_supabase_for_user
from app.schemas.ticket_options import TicketOptionSyncRequest, TicketOptionResponse
from app.services import ticket_option_service, person_service

router = APIRouter()
logger = logging.getLogger(__name__)


def _verify_host(event_id: str, person_id: str, token: str) -> None:
    """Raise 403 if the person is not the host of the event."""
    supabase = get_supabase_for_user(token)
    participation = (
        supabase.table("event_participation")
        .select("event_participation_id")
        .eq("event_id", event_id)
        .eq("person_id", person_id)
        .eq("role", "Host")
        .maybe_single()
        .execute()
    )
    if not participation.data:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.put("/{event_id}/ticket-options", response_model=list[TicketOptionResponse])
async def sync_ticket_options(
    event_id: str,
    body: TicketOptionSyncRequest,
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

        _verify_host(event_id, person_id, credentials.credentials)

        options_data = [opt.model_dump() for opt in body.ticket_options]
        result = ticket_option_service.sync_ticket_options(
            event_id, options_data, credentials.credentials
        )

        return [TicketOptionResponse(**row) for row in result]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ticket options sync error")
        raise HTTPException(status_code=500, detail=str(e))
