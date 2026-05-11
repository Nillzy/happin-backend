"""Event endpoints for listing, viewing, and creating events."""

import logging

from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.auth import get_current_user, get_current_user_optional
from app.schemas.events import (
    EventCreate, EventUpdate, EventListItem, EventListResponse,
    EventDetailResponse, RsvpRequest, RsvpResponse,
)
from app.schemas.ticket_options import TicketOptionResponse
from app.schemas.tickets import ScanTicketRequest, ScanTicketResponse
from app.schemas.custom_fields import CustomFieldResponse
from app.schemas.participants import (
    ParticipantListResponse,
    ParticipantResponse,
    PersonInfo,
    ParticipantCounts,
    CustomFieldResponseItem,
    TicketResponsesItem,
    TicketOptionSummary,
    RemoveParticipantsRequest,
    RemoveParticipantsResponse,
)
from app.services import event_service
from app.services import person_service
from app.services import user_service
from app.services import ticket_service
from app.services import calendar_service
from app.services import google_wallet_service

router = APIRouter()
logger = logging.getLogger(__name__)

optional_bearer = HTTPBearer(auto_error=False)


def _to_list_item(raw: dict) -> EventListItem:
    media = raw.get("event_media") or []
    image_url = media[0]["media_url"] if media else None

    tickets = raw.get("ticket") or []
    participant_count = len(tickets)

    participations = raw.get("event_participation") or []
    rsvp_accepted = sum(1 for p in participations if p.get("status") == "Accepted")
    rsvp_declined = sum(1 for p in participations if p.get("status") == "Declined")
    waitlist_count = sum(1 for p in participations if p.get("status") == "Pending")

    revenue_cents = raw.get("ticket_revenue_cents") or sum(
        int(float((t.get("ticket_option") or {}).get("price", 0)) * 100)
        for t in tickets
        if t.get("ticket_option")
    )

    return EventListItem(
        event_id=raw["event_id"],
        title=raw["title"],
        starts_at=raw["starts_at"],
        ends_at=raw.get("ends_at"),
        description=raw.get("description"),
        category=raw.get("category"),
        max_capacity=raw.get("max_capacity"),
        max_tickets_per_person=raw.get("max_tickets_per_person", 1),
        is_public=raw["is_public"],
        is_free=raw.get("is_free", True),
        status=raw.get("status", "published"),
        image_url=image_url,
        gradient_id=raw.get("gradient_id"),
        location=raw.get("location"),
        participant_count=participant_count,
        is_host=raw.get("is_host", False),
        rsvp_accepted=rsvp_accepted,
        rsvp_declined=rsvp_declined,
        waitlist_count=waitlist_count,
        ticket_revenue_cents=revenue_cents,
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

    raw_events, total_count = event_service.get_public_events(limit=limit, offset=offset, person_id=person_id)
    events = [_to_list_item(e) for e in raw_events]
    return EventListResponse(events=events, count=total_count)


_bearer = HTTPBearer()


def _me_token(credentials=Depends(_bearer)) -> str:
    return credentials.credentials


@router.get("/me", response_model=EventListResponse)
async def get_my_events(
    role: Optional[Literal["organizer", "attendee"]] = Query(None),
    period: Literal["upcoming", "past"] = Query("upcoming"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_user),
    token: str = Depends(_me_token),
):
    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=token,
    )
    raw = user_service.get_user_events(
        person_id=person["person_id"],
        token=token,
        role=role,
        period=period,
        limit=limit,
        offset=offset,
    )
    events = [_to_list_item(e) for e in raw]
    return EventListResponse(events=events, count=len(events))


def _to_detail(raw: dict) -> EventDetailResponse:
    media = raw.get("event_media") or []
    media_urls = [m["media_url"] for m in media]
    image_url = media_urls[0] if media_urls else None

    tickets = raw.get("ticket") or []
    participant_count = len(tickets)

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
        max_tickets_per_person=raw.get("max_tickets_per_person", 1),
        is_public=raw["is_public"],
        is_free=raw.get("is_free", True),
        status=raw.get("status", "published"),
        image_url=image_url,
        gradient_id=raw.get("gradient_id"),
        location=raw.get("location"),
        participant_count=participant_count,
        is_host=raw.get("is_host", False),
        invitation_link=raw.get("invitation_link"),
        created_at=raw.get("created_at"),
        updated_at=raw.get("updated_at"),
        host_name=host_name,
        media_urls=media_urls,
        ticket_options=[
            TicketOptionResponse(**opt)
            for opt in (raw.get("ticket_option") or [])
        ],
        custom_fields=[
            CustomFieldResponse(**f)
            for f in (raw.get("custom_field") or [])
        ],
        my_rsvp_status=raw.get("my_rsvp_status"),
        ticket=raw.get("my_tickets") or [],
    )


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event_detail(
    event_id: str,
    user=Depends(get_current_user_optional),
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
):
    supabase_user_id = user.user.id if user else None
    token = credentials.credentials if credentials else None
    raw = event_service.get_event_by_id(event_id, supabase_user_id, token)
    if not raw:
        raise HTTPException(status_code=404, detail="Event not found")

    if raw.get("status") == "draft" and not raw.get("is_host"):
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

        raw = event_service.create_event(body.model_dump(), person_id, credentials.credentials, user.user.id)
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

        raw = event_service.update_event(event_id, update_data, person_id, credentials.credentials, user.user.id)
        if not raw:
            raise HTTPException(status_code=403, detail="Not authorized to update this event")

        return _to_detail(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Event update error")
        raise HTTPException(status_code=500, detail=str(e))


_RSVP_STATUS_ERRORS = {
    "event_not_found": (404, "Event not found"),
    "event_in_past":   (400, "RSVP not possible after event has started"),
    "public_event_accepted_only": (400, "Public events only allow status 'Accepted'"),
    "event_full": (409, "Event is fully booked"),
}


@router.post("/{event_id}/rsvp", response_model=RsvpResponse)
async def rsvp_to_event(
    event_id: str,
    body: RsvpRequest,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    try:
        raw = event_service.rsvp_event(
            event_id=event_id,
            supabase_user_id=user.user.id,
            email=user.user.email,
            status=body.status,
            token=credentials.credentials,
        )

        person = person_service.get_or_create_person(
            supabase_user_id=user.user.id,
            email=user.user.email,
            token=credentials.credentials,
        )
        person_id = person["person_id"]
        guest_name = " ".join(
            p for p in [person.get("first_name", ""), person.get("last_name", "")] if p
        ).strip() or None

        if body.status == "Accepted":
            from app.core.supabase import get_supabase_for_user
            supabase = get_supabase_for_user(credentials.credentials)
            max_per_person = 1
            try:
                event_row = (
                    supabase.table("event")
                    .select("max_tickets_per_person")
                    .eq("event_id", event_id)
                    .single()
                    .execute()
                )
                max_per_person = (event_row.data or {}).get("max_tickets_per_person") or 1
            except Exception:
                pass
            ticket_count = min(body.ticket_count, max_per_person)
            print(f"[RSVP] guest_names from request: {body.guest_names}")

            ticket_service.create_tickets(
                event_id=event_id,
                person_id=person_id,
                token=credentials.credentials,
                guest_name=guest_name,
                guest_names=body.guest_names,
                quantity=ticket_count,
            )
        elif body.status == "Declined":
            ticket_service.delete_tickets_for_event(event_id=event_id, person_id=person_id, token=credentials.credentials)

        return RsvpResponse(**raw)
    except ValueError as e:
        code, detail = _RSVP_STATUS_ERRORS.get(str(e), (400, str(e)))
        raise HTTPException(status_code=code, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("RSVP error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{event_id}/participants", response_model=ParticipantListResponse)
async def get_participants(
    event_id: str,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Get all participants for an event. Only accessible by the host."""
    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=credentials.credentials,
    )
    person_id = person["person_id"]

    if not event_service.is_user_host(event_id=event_id, person_id=person_id):
        raise HTTPException(status_code=403, detail="Only the host can view participants")

    data = event_service.get_event_participants(event_id=event_id, token=credentials.credentials)

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
            ticket_count=p.get("ticket_count", 0),
            ticket_options_bought=p.get("ticket_options_bought", {}),
            created_at=p.get("created_at"),
            custom_field_responses=[
                CustomFieldResponseItem(
                    custom_field_id=r["custom_field_id"],
                    value=r["value"],
                )
                for tr in (p.get("ticket_responses") or [])
                for r in tr.get("responses", [])
            ],
            ticket_responses=[
                TicketResponsesItem(
                    ticket_id=tr["ticket_id"],
                    guest_name=tr.get("guest_name"),
                    responses=[
                        CustomFieldResponseItem(
                            custom_field_id=r["custom_field_id"],
                            value=r["value"],
                        )
                        for r in tr.get("responses", [])
                    ],
                )
                for tr in (p.get("ticket_responses") or [])
            ],
        )
        for p in data["participants"]
    ]

    return ParticipantListResponse(
        participants=participants,
        counts=ParticipantCounts(**data["counts"]),
        ticket_option_summary=[
            TicketOptionSummary(**s) for s in data.get("ticket_option_summary", [])
        ],
    )


@router.delete("/{event_id}/participants", response_model=RemoveParticipantsResponse)
async def delete_participants(
    event_id: str,
    request: RemoveParticipantsRequest,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Remove participants from an event. Only accessible by the host."""
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


@router.post("/{event_id}/tickets/scan", response_model=ScanTicketResponse)
async def scan_ticket(
    event_id: str,
    body: ScanTicketRequest,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    """Validate and scan a ticket QR code. Only accessible by the host."""
    person = person_service.get_or_create_person(
        supabase_user_id=user.user.id,
        email=user.user.email,
        token=credentials.credentials,
    )
    person_id = person["person_id"]

    if not event_service.is_user_host(event_id=event_id, person_id=person_id):
        raise HTTPException(status_code=403, detail="Only the host can scan tickets")

    try:
        result = ticket_service.validate_ticket(
            event_id=event_id,
            qr_token=body.qr_token,
            token=credentials.credentials,
        )
    except PermissionError as e:
        logger.error("Ticket update blocked by RLS: %s", e)
        raise HTTPException(status_code=500, detail="Ticket konnte nicht als verwendet markiert werden")
    return ScanTicketResponse(**result)


@router.get("/{event_id}/calendar.ics")
async def get_event_calendar(
    event_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
):
    """
    Generate an ICS calendar file for an event.

    Returns a downloadable .ics file that can be imported into
    Apple Calendar, Google Calendar, Outlook, etc.
    """
    token = credentials.credentials if credentials else None
    ics_content = calendar_service.generate_ics(event_id, token)

    if not ics_content:
        raise HTTPException(status_code=404, detail="Event not found")

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="event-{event_id}.ics"'
        },
    )


@router.get("/{event_id}/wallet")
async def get_event_wallet_link(
    event_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
):
    """
    Generate a Google Wallet "Add to Wallet" link for an event.

    Returns a URL that opens the Google Wallet app/website and adds
    the event ticket to the user's wallet.
    """
    if not google_wallet_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google Wallet integration not configured",
        )

    token = credentials.credentials if credentials else None
    wallet_link = google_wallet_service.generate_wallet_link(event_id, token)

    if not wallet_link:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"wallet_url": wallet_link}
