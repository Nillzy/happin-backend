"""Custom field schemas for event form builder."""

from pydantic import BaseModel, field_validator
from typing import Literal


class CustomFieldItem(BaseModel):
    custom_field_id: str | None = None
    label: str
    field_type: Literal["text", "textarea", "single_select", "multi_select"]
    is_required: bool = False
    options: list[str] | None = None
    sort_order: int = 0

    @field_validator("label")
    @classmethod
    def label_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("label must not be empty")
        if len(v) > 200:
            raise ValueError("label must be at most 200 characters")
        return v

    @field_validator("options")
    @classmethod
    def options_valid_for_select(cls, v, info):
        field_type = info.data.get("field_type")
        if field_type in ("single_select", "multi_select"):
            if not v or len(v) < 1:
                raise ValueError("select fields must have at least one option")
        return v


class CustomFieldResponse(BaseModel):
    custom_field_id: str
    label: str
    field_type: str
    is_required: bool
    options: list[str] | None = None
    sort_order: int = 0


class CustomFieldSyncRequest(BaseModel):
    custom_fields: list[CustomFieldItem]


class CustomFieldResponseItem(BaseModel):
    custom_field_id: str
    value: str | list[str]


class CustomFieldResponseSubmit(BaseModel):
    responses: list[CustomFieldResponseItem]


class CustomFieldResponseOut(BaseModel):
    event_participation_id: str
    custom_field_id: str
    value: str | list[str]
