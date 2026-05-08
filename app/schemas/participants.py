"""Participant-related Pydantic schemas."""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any


class PersonInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    person_id: str
    first_name: str
    last_name: str | None = None
    phone_number: str | None = None


class CustomFieldResponseItem(BaseModel):
    custom_field_id: str
    value: Any


class TicketResponsesItem(BaseModel):
    ticket_id: str
    responses: list[CustomFieldResponseItem] = []


class ParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    participation_id: str
    person: PersonInfo
    status: str
    ticket_count: int = 0
    created_at: datetime | None = None
    custom_field_responses: list[CustomFieldResponseItem] = []
    ticket_responses: list[TicketResponsesItem] = []


class ParticipantCounts(BaseModel):
    accepted: int = 0
    declined: int = 0
    pending: int = 0


class ParticipantListResponse(BaseModel):
    participants: list[ParticipantResponse]
    counts: ParticipantCounts


class RemoveParticipantsRequest(BaseModel):
    participation_ids: list[str]


class RemoveParticipantsResponse(BaseModel):
    removed_count: int
