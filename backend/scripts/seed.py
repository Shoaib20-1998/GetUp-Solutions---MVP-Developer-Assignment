"""Seed the database with demo users and representative tickets.

Idempotent: running it twice leaves the same data rather than duplicating it.

The sample set deliberately includes at least one resolved ticket and one
ticket created more than 48 hours ago, so the admin dashboard has non-trivial
values for average time to resolution and the ageing-ticket count.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Activity, Comment, Ticket, User
from app.models.enums import Category, EventType, Priority, Role, Status
from app.services.auth import hash_password

DEMO_PASSWORD = "Password123!"

DEMO_USERS = [
    ("admin@example.com", "Avery Admin", Role.ADMIN),
    ("agent@example.com", "Robin Agent", Role.AGENT),
    ("agent2@example.com", "Sam Agent", Role.AGENT),
    ("customer@example.com", "Casey Customer", Role.CUSTOMER),
    ("customer2@example.com", "Devon Customer", Role.CUSTOMER),
]

now = datetime.now(UTC)

# (title, description, category, priority, status, requester, assignee, age_hours)
SAMPLE_TICKETS = [
    (
        "Invoice charged twice this month",
        "My card was charged two times for the April subscription. Please refund the duplicate.",
        Category.BILLING,
        Priority.HIGH,
        Status.OPEN,
        "customer@example.com",
        "agent@example.com",
        72,
    ),
    (
        "Cannot reset my password",
        "The reset email never arrives. I have checked spam. Account is locked out now.",
        Category.ACCOUNT,
        Priority.URGENT,
        Status.IN_PROGRESS,
        "customer@example.com",
        "agent@example.com",
        30,
    ),
    (
        "Export to CSV times out",
        "Exporting a report with more than 10k rows spins for a minute then fails.",
        Category.TECHNICAL,
        Priority.MEDIUM,
        Status.RESOLVED,
        "customer@example.com",
        "agent@example.com",
        96,
    ),
    (
        "How do I add a teammate?",
        "I want to invite a colleague to our workspace but cannot find the option.",
        Category.GENERAL,
        Priority.LOW,
        Status.CLOSED,
        "customer2@example.com",
        "agent2@example.com",
        120,
    ),
    (
        "Dashboard graphs render blank",
        "On Safari the analytics charts are empty. Chrome is fine.",
        Category.TECHNICAL,
        Priority.HIGH,
        Status.OPEN,
        "customer2@example.com",
        None,
        80,
    ),
    (
        "Upgrade to the annual plan",
        "Please switch our billing to annual and apply the discount.",
        Category.BILLING,
        Priority.LOW,
        Status.IN_PROGRESS,
        "customer2@example.com",
        "agent2@example.com",
        6,
    ),
    (
        "Two factor codes rejected",
        "Authenticator codes are refused even though the clock is in sync.",
        Category.ACCOUNT,
        Priority.URGENT,
        Status.RESOLVED,
        "customer@example.com",
        "agent2@example.com",
        60,
    ),
]


def seed() -> None:
    db = SessionLocal()
    try:
        users: dict[str, User] = {}
        for email, full_name, role in DEMO_USERS:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    full_name=full_name,
                    role=role,
                    password_hash=hash_password(DEMO_PASSWORD),
                )
                db.add(user)
                db.flush()
            users[email] = user

        for (
            title,
            description,
            category,
            priority,
            status,
            requester_email,
            assignee_email,
            age_hours,
        ) in SAMPLE_TICKETS:
            if db.scalar(select(Ticket).where(Ticket.title == title)) is not None:
                continue

            created_at = now - timedelta(hours=age_hours)
            resolved_at = None
            if status in (Status.RESOLVED, Status.CLOSED):
                # Resolved partway through the ticket's life, so average
                # time-to-resolution is a realistic figure rather than zero.
                resolved_at = created_at + timedelta(hours=age_hours / 2)

            ticket = Ticket(
                title=title,
                description=description,
                category=category,
                priority=priority,
                status=status,
                requester_id=users[requester_email].id,
                assignee_id=users[assignee_email].id if assignee_email else None,
                created_at=created_at,
                resolved_at=resolved_at,
            )
            db.add(ticket)
            db.flush()

            db.add(
                Activity(
                    ticket_id=ticket.id,
                    actor_id=ticket.requester_id,
                    event_type=EventType.CREATED,
                    to_value=Status.OPEN.value,
                    created_at=created_at,
                )
            )
            if assignee_email:
                db.add(
                    Activity(
                        ticket_id=ticket.id,
                        actor_id=users["admin@example.com"].id,
                        event_type=EventType.ASSIGNED,
                        to_value=assignee_email,
                        created_at=created_at + timedelta(minutes=5),
                    )
                )
                db.add(
                    Comment(
                        ticket_id=ticket.id,
                        author_id=users[assignee_email].id,
                        body="Thanks for reporting this, I am taking a look now.",
                        is_internal=False,
                        created_at=created_at + timedelta(minutes=30),
                    )
                )
                db.add(
                    Comment(
                        ticket_id=ticket.id,
                        author_id=users[assignee_email].id,
                        body="Internal: reproduced on staging, needs a backend fix.",
                        is_internal=True,
                        created_at=created_at + timedelta(minutes=35),
                    )
                )

        db.commit()

        total = db.scalar(select(Ticket).with_only_columns(Ticket.id).exists().select())
        print(f"seeded users={len(users)} tickets_present={bool(total)}")
        print(f"demo password for every account: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
