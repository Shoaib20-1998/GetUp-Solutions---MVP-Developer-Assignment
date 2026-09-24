import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Category, Priority, Status
from app.schemas.auth import UserResponse


def _reject_nul_bytes(value: str) -> str:
    # Postgres text columns cannot store NUL (0x00); a string containing one
    # would pass length/emptiness checks here but 500 at the database layer.
    # Rejecting it here turns that into a clean 422 instead.
    if "\x00" in value:
        raise ValueError("must not contain NUL characters")
    return value


class TicketCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    category: Category
    priority: Priority

    @field_validator("title", "description")
    @classmethod
    def _no_nul_bytes(cls, value: str) -> str:
        return _reject_nul_bytes(value)


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    category: Category
    priority: Priority
    status: Status
    requester: UserResponse
    assignee: UserResponse | None

    ai_suggested_category: Category | None
    ai_suggested_priority: Priority | None
    ai_summary: str | None
    ai_draft_reply: str | None

    resolved_at: datetime | None
    created_at: datetime


class TicketDetailResponse(TicketResponse):
    """Comments are fetched separately via `/comments` since visibility
    depends on the caller's role (internal notes are redacted for a
    Customer) -- logic that belongs with the comments endpoints, not here."""

    attachments: list[AttachmentResponse]


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int
    page: int
    page_size: int
