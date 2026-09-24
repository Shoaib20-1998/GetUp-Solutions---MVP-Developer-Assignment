"""The single place ticket visibility is decided.

Every ticket query, list or single-row, passes through `scope_tickets` before
any filter, search, or pagination is applied. Routers and other services never
build a `select(Ticket)` themselves, so a restriction added here cannot be
bypassed by forgetting to call it elsewhere (Requirement 2.2).
"""

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Role, Ticket, User


def scope_tickets(query: Select, user: User) -> Select:
    """Narrow `query` to the tickets `user` is entitled to see.

    Admin sees everything. Agent sees tickets assigned to them. Customer sees
    tickets they requested. This ordering (role-based scope first) is what
    Requirement 5.4 relies on when filters and search are layered on top.
    """
    if user.role is Role.ADMIN:
        return query
    if user.role is Role.AGENT:
        return query.where(Ticket.assignee_id == user.id)
    return query.where(Ticket.requester_id == user.id)


def get_scoped_ticket(db: Session, ticket_id: uuid.UUID, user: User) -> Ticket | None:
    """Fetch a single ticket through the same scoping rule.

    Returns None both when the ticket does not exist and when it exists but
    the caller is not entitled to it. Callers raise 404 in either case, which
    is what makes unentitled access indistinguishable from absence
    (Requirement 2.6).
    """
    query = scope_tickets(select(Ticket).where(Ticket.id == ticket_id), user)
    return db.scalars(query).first()


def is_participant(ticket: Ticket, user: User) -> bool:
    """Whether `user` may act on `ticket` as a participant: the requester,
    the assigned agent, or any admin. This is the same set entitled to see
    the ticket at all (Requirement 2.6), reused for comments and attachments
    so "who may act" cannot drift from "who may see"."""
    if user.role is Role.ADMIN:
        return True
    if user.role is Role.AGENT:
        return ticket.assignee_id == user.id
    return ticket.requester_id == user.id
