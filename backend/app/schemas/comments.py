import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import UserResponse


class CommentCreateRequest(BaseModel):
    body: str = Field(min_length=1)
    is_internal: bool = False


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    author: UserResponse
    body: str
    is_internal: bool
    created_at: datetime
