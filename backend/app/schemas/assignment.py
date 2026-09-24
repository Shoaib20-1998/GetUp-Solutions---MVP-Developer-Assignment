import uuid

from pydantic import BaseModel


class AssignmentRequest(BaseModel):
    assignee_id: uuid.UUID
