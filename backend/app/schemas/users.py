import uuid

from pydantic import BaseModel, ConfigDict


class UserSummary(BaseModel):
    """Minimal user shape for pickers (e.g. the assignment dropdown). Not
    the full UserResponse, since callers only need id + display name."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
