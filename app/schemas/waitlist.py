"""Pydantic schemas for waitlist endpoints."""

from pydantic import BaseModel


class WaitlistJoinResponse(BaseModel):
    waitlist_id: str
    position: int


class WaitlistPositionResponse(BaseModel):
    position: int
