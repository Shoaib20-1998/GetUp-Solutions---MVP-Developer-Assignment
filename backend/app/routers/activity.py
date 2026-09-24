import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Activity, Role, User
from app.schemas.activity import ActivityResponse
from app.services.scoping import get_scoped_ticket

router = APIRouter(prefix="/api/tickets/{ticket_id}/activity", tags=["activity"])


@router.get(
    "",
    response_model=list[ActivityResponse],
    summary="Get a ticket's audit trail",
    responses={
        403: {"description": "Only Agent or Admin may view the activity log"},
        404: {"description": "Not found, or not visible to the caller"},
    },
)
def list_activity(
    ticket_id: uuid.UUID,
    user: Annotated[User, Depends(require_role(Role.AGENT, Role.ADMIN))],
    db: Session = Depends(get_db),
) -> list[Activity]:
    ticket = get_scoped_ticket(db, ticket_id, user)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    query = select(Activity).where(Activity.ticket_id == ticket.id)
    return list(db.scalars(query.order_by(Activity.created_at.asc())).all())
