from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Role, User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import build_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Queue health metrics",
    responses={403: {"description": "Admin only"}},
)
def get_dashboard(
    _: Annotated[User, Depends(require_role(Role.ADMIN))],
    db: Session = Depends(get_db),
) -> DashboardResponse:
    return build_dashboard(db)
