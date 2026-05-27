"""Custom field endpoints — form definitions + guest responses."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer

from app.core.auth import get_current_user, get_current_user_optional
from app.schemas.custom_fields import (
    CustomFieldSyncRequest,
    CustomFieldResponse,
    CustomFieldResponseSubmit,
    CustomFieldResponseItem,
    TicketResponsesOut,
)
from app.services import custom_field_service, person_service, event_service

router = APIRouter()
logger = logging.getLogger(__name__)


def _verify_host(event_id: str, person_id: str) -> None:
    if not event_service.is_user_host(event_id, person_id):
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{event_id}/custom-fields", response_model=list[CustomFieldResponse])
async def get_custom_fields(
    event_id: str,
    user=Depends(get_current_user_optional),
):
    try:
        result = custom_field_service.get_custom_fields(event_id)
        return [CustomFieldResponse(**row) for row in result]
    except Exception as e:
        logger.exception("Get custom fields error")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{event_id}/custom-fields", response_model=list[CustomFieldResponse])
async def sync_custom_fields(
    event_id: str,
    body: CustomFieldSyncRequest,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    try:
        person = person_service.get_or_create_person(
            supabase_user_id=user.user.id,
            email=user.user.email,
            token=credentials.credentials,
        )
        _verify_host(event_id, person["person_id"])

        fields_data = [f.model_dump() for f in body.custom_fields]
        result = custom_field_service.sync_custom_fields(
            event_id, fields_data, credentials.credentials
        )
        return [CustomFieldResponse(**row) for row in result]
    except HTTPException:
        raise
    except ValueError as e:
        if str(e) == "event_cancelled":
            raise HTTPException(status_code=400, detail="Event wurde abgesagt und kann nicht mehr verändert werden")
        if str(e) == "event_not_found":
            raise HTTPException(status_code=404, detail="Event nicht gefunden")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Custom fields sync error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{event_id}/custom-fields/responses",
    response_model=list[CustomFieldResponseItem],
)
async def submit_responses(
    event_id: str,
    body: CustomFieldResponseSubmit,
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

        from app.core.supabase import get_supabase_for_user
        from app.services.event_service import _ensure_event_active

        _ensure_event_active(event_id, credentials.credentials)
        supabase = get_supabase_for_user(credentials.credentials)
        ticket = (
            supabase.table("ticket")
            .select("ticket_id")
            .eq("ticket_id", body.ticket_id)
            .eq("event_id", event_id)
            .eq("person_id", person_id)
            .maybe_single()
            .execute()
        )
        if not ticket.data:
            raise HTTPException(
                status_code=400, detail="Ticket not found or does not belong to you"
            )

        responses_data = [r.model_dump() for r in body.responses]
        result = custom_field_service.submit_responses(
            body.ticket_id, responses_data, credentials.credentials
        )
        return [CustomFieldResponseItem(**row) for row in result]
    except HTTPException:
        raise
    except ValueError as e:
        if str(e) == "event_cancelled":
            raise HTTPException(status_code=400, detail="Event wurde abgesagt und kann nicht mehr verändert werden")
        if str(e) == "event_not_found":
            raise HTTPException(status_code=404, detail="Event nicht gefunden")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Submit responses error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{event_id}/custom-fields/responses/me",
    response_model=list[TicketResponsesOut],
)
async def get_my_responses(
    event_id: str,
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

        result = custom_field_service.get_my_responses(
            event_id, person_id, credentials.credentials
        )
        return [
            TicketResponsesOut(
                ticket_id=item["ticket_id"],
                responses=[CustomFieldResponseItem(**r) for r in item["responses"]],
            )
            for item in result
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Get my responses error")
        raise HTTPException(status_code=500, detail=str(e))
