from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Role, User
from app.schemas.users import UserSummary

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserSummary],
    summary="List users by role (Admin only)",
    responses={403: {"description": "Admin only"}},
)
def list_users(
    _: Annotated[User, Depends(require_role(Role.ADMIN))],
    role: Role | None = None,
    db: Session = Depends(get_db),
) -> list[User]:
    # Scoped to a narrow purpose: powering the assignment picker. Not a
    # general user directory -- Admin only, and typically filtered to
    # role=agent by the caller.
    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    return list(db.scalars(query.order_by(User.full_name)).all())
