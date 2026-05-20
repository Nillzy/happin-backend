"""Ticket booking endpoint — creates tickets and sets implicit RSVP."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer

from app.core.auth import get_current_user
from app.core.supabase import get_supabase_for_user
from app.schemas.tickets import CreateTicketsRequest, CreateTicketsResponse
from app.services import booking_service, event_service, person_service, ticket_service

logger = logging.getLogger(__name__)

router = APIRouter()

_BOOKING_ERRORS = {
    "event_not_found": (404, "Event not found"),
    "event_full": (409, "Event is fully booked"),
    "ticket_option_wrong_event": (400, "Ticket option does not belong to this event"),
    "ticket_option_sold_out": (409, "Ticket option sold out"),
    "payment_required": (400, "Paid tickets require checkout — use /checkout-session"),
    "max_tickets_exceeded": (409, "Maximum tickets per person exceeded"),
    "checkout_pending": (409, "You already have a pending checkout for this event"),
}


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
        guest_name = " ".join(
            p for p in [person.get("first_name", ""), person.get("last_name", "")] if p
        ).strip() or None

        supabase = get_supabase_for_user(token)

        booking_service.validate_booking(
            supabase,
            event_id=event_id,
            person_id=person_id,
            quantity=body.quantity,
            ticket_option_id=body.ticket_option_id,
            allow_free_only=True,
        )

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
            guest_name=guest_name,
        )

        return CreateTicketsResponse(tickets=tickets)
    except ValueError as e:
        code, detail = _BOOKING_ERRORS.get(str(e), (400, str(e)))
        raise HTTPException(status_code=code, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ticket creation error")
        raise HTTPException(status_code=500, detail=str(e))
