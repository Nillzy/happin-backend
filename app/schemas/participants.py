"""Participant-related Pydantic schemas."""

from pydantic import BaseModel
from datetime import datetime


class PersonInfo(BaseModel):
    person_id: str
    first_name: str
    last_name: str | None = None
    phone_number: str | None = None

    class Config:
        from_attributes = True


class ParticipantResponse(BaseModel):
    participation_id: str
    person: PersonInfo
    status: str
    created_at: datetime | None = None

    class Config:
        from_attributes = True


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
