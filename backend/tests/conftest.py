"""Shared pytest fixtures.

The test database is real Postgres, never mocked (Requirement 15.5). The
schema is built once per session via `Base.metadata.create_all`, and every
test runs inside a transaction that is rolled back afterwards so tests
cannot see each other's data without needing a fresh database per test.
"""

import os
import tempfile
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://ticketing:ticketing@localhost:5432/ticketing_test",
)
# Overridable so a local run against a differently-mapped Postgres port
# (e.g. this sandbox's tkt-pg on 55432) doesn't require editing this file.
if "TEST_DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-use-only")
# The production default (/data/attachments) is a container-mounted volume;
# outside Docker there is no writable /data, so tests point this at a real,
# writable temp directory instead. Requirement 12.1 (config from the
# environment) is exactly why this can be overridden without touching code.
os.environ.setdefault("ATTACHMENT_DIR", tempfile.mkdtemp(prefix="ticketing_test_attachments_"))

from app.ai.mock_provider import MockAIProvider  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Category, Priority, Role, Ticket, User  # noqa: E402
from app.services import triage  # noqa: E402
from app.services.auth import hash_password  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(get_settings().database_url)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    outer_transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    # Nested SAVEPOINT so a test's own commit() calls don't end the outer
    # transaction early; restart the savepoint each time one closes.
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    triage.set_provider(MockAIProvider())
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class UserFactory:
    def __init__(self, db_session: Session):
        self._db = db_session

    def create(self, role: Role = Role.CUSTOMER, password: str = "correct-password") -> User:
        user = User(
            email=f"{uuid.uuid4()}@example.com",
            full_name="Test User",
            password_hash=hash_password(password),
            role=role,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user


class TicketFactory:
    def __init__(self, db_session: Session):
        self._db = db_session

    def create(
        self,
        requester: User,
        assignee: User | None = None,
        **overrides,
    ) -> Ticket:
        ticket = Ticket(
            title=overrides.get("title", "Sample issue"),
            description=overrides.get("description", "Something needs fixing."),
            category=overrides.get("category", Category.GENERAL),
            priority=overrides.get("priority", Priority.MEDIUM),
            status=overrides.get("status", "open"),
            requester_id=requester.id,
            assignee_id=assignee.id if assignee else None,
        )
        self._db.add(ticket)
        self._db.commit()
        self._db.refresh(ticket)
        return ticket


@pytest.fixture
def user_factory(db_session) -> UserFactory:
    return UserFactory(db_session)


@pytest.fixture
def ticket_factory(db_session) -> TicketFactory:
    return TicketFactory(db_session)


def auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
