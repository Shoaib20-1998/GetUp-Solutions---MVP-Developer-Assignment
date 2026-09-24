import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import EventType
from app.schemas.auth import UserResponse


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    actor: UserResponse | None
    event_type: EventType
    from_value: str | None
    to_value: str | None
    created_at: datetime
