import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Category, EventType, Priority, Role, Status


def _enum(python_enum: type, name: str) -> SAEnum:
    """Persist enum *values* rather than member names."""
    return SAEnum(
        python_enum,
        name=name,
        values_callable=lambda e: [member.value for member in e],
    )


# Defined once and reused, so PostgreSQL emits a single CREATE TYPE per enum
# even where two columns share a type (category / ai_suggested_category).
ROLE_ENUM = _enum(Role, "role_enum")
STATUS_ENUM = _enum(Status, "status_enum")
PRIORITY_ENUM = _enum(Priority, "priority_enum")
CATEGORY_ENUM = _enum(Category, "category_enum")
EVENT_TYPE_ENUM = _enum(EventType, "event_type_enum")


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(ROLE_ENUM, default=Role.CUSTOMER)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = _pk()
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[Category] = mapped_column(CATEGORY_ENUM)
    priority: Mapped[Priority] = mapped_column(PRIORITY_ENUM, index=True)
    status: Mapped[Status] = mapped_column(STATUS_ENUM, default=Status.OPEN, index=True)

    requester_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # AI suggestions live in their own namespace and are never written to the
    # real `category` / `priority` columns except via the confirmation endpoint.
    ai_suggested_category: Mapped[Category | None] = mapped_column(
        CATEGORY_ENUM, nullable=True
    )
    ai_suggested_priority: Mapped[Priority | None] = mapped_column(
        PRIORITY_ENUM, nullable=True
    )
    ai_summary: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ai_draft_reply: Mapped[str | None] = mapped_column(Text, nullable=True)

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    requester: Mapped["User"] = relationship(foreign_keys=[requester_id], lazy="joined")
    assignee: Mapped["User | None"] = relationship(
        foreign_keys=[assignee_id], lazy="joined"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = _pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(lazy="joined")


class Activity(Base):
    """Append-only audit trail. No update or delete route is exposed."""

    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = _pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[EventType] = mapped_column(EVENT_TYPE_ENUM)
    from_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    to_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    actor: Mapped["User | None"] = relationship(lazy="joined")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = _pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(127))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="attachments")
