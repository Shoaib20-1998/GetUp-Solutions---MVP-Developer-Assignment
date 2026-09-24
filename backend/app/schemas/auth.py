import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role


class RegisterRequest(BaseModel):
    """Any `role` supplied by the caller is ignored: registration always
    produces a Customer (Requirement 2.8). The field is not declared at all,
    and `extra="ignore"` means sending it is silently discarded rather than
    rejected, so a hostile payload cannot escalate."""

    model_config = ConfigDict(extra="ignore")

    email: EmailStr
    password: str = Field(min_length=8, description="At least 8 characters")
    full_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    created_at: datetime
