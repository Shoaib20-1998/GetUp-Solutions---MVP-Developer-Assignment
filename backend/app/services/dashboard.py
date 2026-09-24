"""Aggregate queue-health metrics for the admin dashboard."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Priority, Status, Ticket
from app.schemas.dashboard import DashboardResponse

_STALE_THRESHOLD = timedelta(hours=48)


def build_dashboard(db: Session) -> DashboardResponse:
    status_rows = db.execute(
        select(Ticket.status, func.count()).group_by(Ticket.status)
    ).all()
    counts_by_status = dict.fromkeys(Status, 0)
    counts_by_status.update({row[0]: row[1] for row in status_rows})

    priority_rows = db.execute(
        select(Ticket.priority, func.count()).group_by(Ticket.priority)
    ).all()
    counts_by_priority = dict.fromkeys(Priority, 0)
    counts_by_priority.update({row[0]: row[1] for row in priority_rows})

    # Average resolution time as null, not zero, when nothing has resolved
    # yet (Requirement 10.4) -- a zero would misleadingly imply instant
    # resolution rather than "no data".
    avg_seconds = db.scalar(
        select(
            func.avg(
                func.extract("epoch", Ticket.resolved_at - Ticket.created_at)
            )
        ).where(Ticket.resolved_at.is_not(None))
    )
    average_resolution_hours = (avg_seconds / 3600) if avg_seconds is not None else None

    stale_cutoff = datetime.now(UTC) - _STALE_THRESHOLD
    stale_open_count = db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.status == Status.OPEN, Ticket.created_at < stale_cutoff)
    ) or 0

    return DashboardResponse(
        counts_by_status=counts_by_status,
        counts_by_priority=counts_by_priority,
        average_resolution_hours=average_resolution_hours,
        stale_open_count=stale_open_count,
    )
