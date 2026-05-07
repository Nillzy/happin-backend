"""Ticket booking endpoint — creates tickets and sets implicit RSVP."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer

from app.core.auth import get_current_user
from app.core.supabase import get_supabase_for_user
from app.schemas.tickets import CreateTicketsRequest, CreateTicketsResponse
from app.services import event_service, person_service, ticket_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{event_id}/tickets", response_model=CreateTicketsResponse)
async def create_tickets(
    event_id: str,
    body: CreateTicketsRequest,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Book one or more tickets for an event. Implicitly sets RSVP to Accepted."""
    token = credentials.credentials
    try:
        person = person_service.get_or_create_person(
            supabase_user_id=user.user.id,
            email=user.user.email,
            token=token,
        )
        person_id = person["person_id"]

        # Capacity check: current tickets + requested quantity must fit
        supabase = get_supabase_for_user(token)
        event_row = (
            supabase.table("event")
            .select("max_capacity")
            .eq("event_id", event_id)
            .maybe_single()
            .execute()
        )
        if not event_row.data:
            raise ValueError("event_not_found")

        max_cap = event_row.data.get("max_capacity")
        if max_cap is not None:
            current_count = (
                supabase.table("ticket")
                .select("ticket_id", count="exact")
                .eq("event_id", event_id)
                .execute()
            ).count or 0
            if current_count + body.quantity > int(max_cap):
                raise ValueError("event_full")

        event_service.rsvp_event(
            event_id=event_id,
            supabase_user_id=user.user.id,
            email=user.user.email,
            status="Accepted",
            token=token,
        )

        tickets = ticket_service.create_tickets(
            event_id=event_id,
            person_id=person_id,
            token=token,
            ticket_option_id=body.ticket_option_id,
            quantity=body.quantity,
        )

        return CreateTicketsResponse(tickets=tickets)
    except ValueError as e:
        error_map = {
            "event_not_found": (404, "Event not found"),
            "event_in_past": (400, "Event has already started"),
            "event_full": (409, "Event is fully booked"),
        }
        code, detail = error_map.get(str(e), (400, str(e)))
        raise HTTPException(status_code=code, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ticket creation error")
        raise HTTPException(status_code=500, detail=str(e))
