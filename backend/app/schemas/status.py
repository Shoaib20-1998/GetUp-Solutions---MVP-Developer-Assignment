from pydantic import BaseModel

from app.models.enums import Status


class StatusUpdateRequest(BaseModel):
    status: Status
