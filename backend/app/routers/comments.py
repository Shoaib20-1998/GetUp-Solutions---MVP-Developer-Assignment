import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import CurrentUser
from app.models import Comment, Role, Ticket, User
from app.schemas.comments import CommentCreateRequest, CommentResponse
from app.services.scoping import get_scoped_ticket, is_participant

router = APIRouter(prefix="/api/tickets/{ticket_id}/comments", tags=["comments"])


def _get_ticket_for_participant(db: Session, ticket_id: uuid.UUID, user: User) -> Ticket:
    ticket = get_scoped_ticket(db, ticket_id, user)
    if ticket is None or not is_participant(ticket, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.get(
    "",
    response_model=list[CommentResponse],
    summary="List a ticket's comments",
    responses={404: {"description": "Not found, or not visible to the caller"}},
)
def list_comments(
    ticket_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[Comment]:
    ticket = _get_ticket_for_participant(db, ticket_id, user)

    query = select(Comment).where(Comment.ticket_id == ticket.id)
    if user.role is Role.CUSTOMER:
        # Internal notes are never sent to the client, not merely hidden by
        # the UI (Requirement 7.4).
        query = query.where(Comment.is_internal.is_(False))

    return list(db.scalars(query.order_by(Comment.created_at.asc())).all())


@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a comment or internal note",
    responses={
        403: {"description": "A Customer may not create an internal note"},
        404: {"description": "Not found, or not visible to the caller"},
    },
)
def create_comment(
    ticket_id: uuid.UUID,
    payload: CommentCreateRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> Comment:
    ticket = _get_ticket_for_participant(db, ticket_id, user)

    if payload.is_internal and user.role is Role.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers may not create internal notes",
        )

    comment = Comment(
        ticket_id=ticket.id,
        author_id=user.id,
        body=payload.body,
        is_internal=payload.is_internal,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
