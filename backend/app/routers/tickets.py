from typing import Annotated

import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import CurrentUser, require_role
from app.models import Activity, Attachment, Priority, Role, Status, Ticket, User
from app.models.enums import EventType
from app.schemas.ai import ApplySuggestionRequest, SuggestionField
from app.schemas.assignment import AssignmentRequest
from app.schemas.status import StatusUpdateRequest
from app.schemas.tickets import (
    AttachmentResponse,
    TicketCreateRequest,
    TicketDetailResponse,
    TicketListResponse,
    TicketResponse,
)
from app.services.scoping import get_scoped_ticket, is_participant, scope_tickets
from app.services.triage import apply_triage

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

_TICKET_NOT_FOUND = "Ticket not found"

# Declared as data, not branching logic, so Requirement 4.3 (an illegal
# transition is rejected and leaves state unchanged) is verifiable by
# inspection rather than by tracing conditionals.
_ALLOWED_TRANSITIONS: dict[Status, set[Status]] = {
    Status.OPEN: {Status.IN_PROGRESS},
    Status.IN_PROGRESS: {Status.RESOLVED},
    Status.RESOLVED: {Status.CLOSED},
    Status.CLOSED: set(),
}


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ticket",
    responses={
        403: {"description": "Only a Customer may create a ticket"},
        422: {"description": "Validation error"},
    },
)
def create_ticket(
    payload: TicketCreateRequest,
    user: Annotated[User, Depends(require_role(Role.CUSTOMER))],
    db: Session = Depends(get_db),
) -> Ticket:
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        requester_id=user.id,
    )
    db.add(ticket)
    db.flush()

    db.add(
        Activity(
            ticket_id=ticket.id,
            actor_id=user.id,
            event_type=EventType.CREATED,
            from_value=None,
            to_value=ticket.status.value,
        )
    )
    db.commit()
    db.refresh(ticket)

    return apply_triage(db, ticket)


@router.get(
    "",
    response_model=TicketListResponse,
    summary="List tickets visible to the caller",
)
def list_tickets(
    user: CurrentUser,
    status_filter: Annotated[Status | None, Query(alias="status")] = None,
    priority: Priority | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    db: Session = Depends(get_db),
) -> TicketListResponse:
    settings = get_settings()
    size = min(page_size or settings.default_page_size, settings.max_page_size)

    # Role-based visibility is applied before any filter, search, or
    # pagination (Requirement 5.4).
    query = scope_tickets(select(Ticket), user)

    if status_filter is not None:
        query = query.where(Ticket.status == status_filter)
    if priority is not None:
        query = query.where(Ticket.priority == priority)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            or_(Ticket.title.ilike(pattern), Ticket.description.ilike(pattern))
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    items = (
        db.scalars(
            query.order_by(Ticket.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        .all()
    )

    return TicketListResponse(items=items, total=total, page=page, page_size=size)


@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Get a single ticket",
    responses={404: {"description": "Not found, or not visible to the caller"}},
)
def get_ticket(
    ticket_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> Ticket:
    # Absence and lack of entitlement are deliberately indistinguishable
    # (Requirement 2.6): both produce 404, never a 403 that would confirm the
    # ticket exists.
    ticket = get_scoped_ticket(db, ticket_id, user)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_TICKET_NOT_FOUND)
    return ticket


@router.post(
    "/{ticket_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a file to a ticket",
    responses={
        404: {"description": "Not found, or not visible to the caller"},
        413: {"description": "File exceeds the configured size limit"},
        415: {"description": "Content type not allowed"},
    },
)
def upload_attachment(
    ticket_id: uuid.UUID,
    user: CurrentUser,
    file: UploadFile,
    db: Session = Depends(get_db),
) -> Attachment:
    ticket = get_scoped_ticket(db, ticket_id, user)
    if ticket is None or not is_participant(ticket, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_TICKET_NOT_FOUND)

    settings = get_settings()

    if file.content_type not in settings.allowed_attachment_type_set:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Attachment content type is not allowed",
        )

    body = file.file.read()
    if len(body) > settings.max_attachment_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Attachment exceeds the maximum allowed size",
        )

    os.makedirs(settings.attachment_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4()}_{file.filename}"
    storage_path = os.path.join(settings.attachment_dir, stored_name)
    with open(storage_path, "wb") as f:
        f.write(body)

    attachment = Attachment(
        ticket_id=ticket.id,
        filename=file.filename or stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(body),
        storage_path=storage_path,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.patch(
    "/{ticket_id}/status",
    response_model=TicketResponse,
    summary="Transition a ticket's status",
    responses={
        403: {"description": "Only Agent or Admin may change status"},
        404: {"description": "Not found, or not visible to the caller"},
        409: {"description": "Transition not permitted by the workflow"},
    },
)
def update_status(
    ticket_id: uuid.UUID,
    payload: StatusUpdateRequest,
    user: Annotated[User, Depends(require_role(Role.AGENT, Role.ADMIN))],
    db: Session = Depends(get_db),
) -> Ticket:
    ticket = get_scoped_ticket(db, ticket_id, user)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_TICKET_NOT_FOUND)

    current = ticket.status
    target = payload.status
    if target not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from {current.value} to {target.value}",
        )

    ticket.status = target
    if target is Status.RESOLVED:
        ticket.resolved_at = datetime.now(UTC)

    db.add(
        Activity(
            ticket_id=ticket.id,
            actor_id=user.id,
            event_type=EventType.STATUS_CHANGED,
            from_value=current.value,
            to_value=target.value,
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch(
    "/{ticket_id}/assignee",
    response_model=TicketResponse,
    summary="Assign or reassign a ticket to an Agent",
    responses={
        403: {"description": "Only Admin may assign tickets"},
        404: {"description": "Not found, or not visible to the caller"},
        422: {"description": "Target user is not an Agent"},
    },
)
def update_assignee(
    ticket_id: uuid.UUID,
    payload: AssignmentRequest,
    user: Annotated[User, Depends(require_role(Role.ADMIN))],
    db: Session = Depends(get_db),
) -> Ticket:
    ticket = get_scoped_ticket(db, ticket_id, user)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_TICKET_NOT_FOUND)

    target = db.get(User, payload.assignee_id)
    if target is None or target.role is not Role.AGENT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assignee must be an existing user with the Agent role",
        )

    previous_assignee_id = ticket.assignee_id
    ticket.assignee_id = target.id

    db.add(
        Activity(
            ticket_id=ticket.id,
            actor_id=user.id,
            event_type=EventType.ASSIGNED,
            from_value=str(previous_assignee_id) if previous_assignee_id else None,
            to_value=str(target.id),
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post(
    "/{ticket_id}/ai/apply",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm an AI suggestion, applying it to the real field",
    responses={
        403: {"description": "Only Agent or Admin may confirm a suggestion"},
        404: {"description": "Not found, or not visible to the caller"},
        409: {"description": "No suggestion available for the requested field"},
    },
)
def apply_ai_suggestion(
    ticket_id: uuid.UUID,
    payload: ApplySuggestionRequest,
    user: Annotated[User, Depends(require_role(Role.AGENT, Role.ADMIN))],
    db: Session = Depends(get_db),
) -> Ticket:
    # This is the only code path that may write a suggestion into a real
    # field (Requirement 9.3). No other endpoint touches `category` or
    # `priority` from the `ai_suggested_*` columns.
    ticket = get_scoped_ticket(db, ticket_id, user)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_TICKET_NOT_FOUND)

    if payload.field is SuggestionField.CATEGORY:
        if ticket.ai_suggested_category is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No category suggestion is available for this ticket",
            )
        previous = ticket.category.value
        ticket.category = ticket.ai_suggested_category
        new_value = ticket.category.value
    else:
        if ticket.ai_suggested_priority is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No priority suggestion is available for this ticket",
            )
        previous = ticket.priority.value
        ticket.priority = ticket.ai_suggested_priority
        new_value = ticket.priority.value

    db.add(
        Activity(
            ticket_id=ticket.id,
            actor_id=user.id,
            event_type=EventType.AI_APPLIED,
            from_value=f"{payload.field.value}:{previous}",
            to_value=f"{payload.field.value}:{new_value}",
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket
