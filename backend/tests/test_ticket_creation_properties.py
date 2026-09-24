"""Property-based tests for ticket creation. See design.md's Correctness
Properties section (P8, P9).
"""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.models import Category, Priority, Role, Ticket
from tests.conftest import auth_headers

valid_text = st.text(min_size=1, max_size=200).filter(
    lambda s: s.strip() and "\x00" not in s
)
category_strategy = st.sampled_from(list(Category))
priority_strategy = st.sampled_from(list(Priority))

# Deliberately outside the real enum, but shaped like a plausible bad input:
# a random token or a near-miss on a real value ("Low" vs "low").
invalid_enum_value = st.text(min_size=1, max_size=20).filter(
    lambda s: s not in {c.value for c in Category} and s not in {p.value for p in Priority}
)


class TestP8CreationInvariants:
    """P8 -- Validates: Requirements 3.1"""

    @given(
        title=valid_text,
        description=valid_text,
        category=category_strategy,
        priority=priority_strategy,
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        max_examples=25,
    )
    def test_valid_creation_always_succeeds_as_open(
        self, client, user_factory, title, description, category, priority
    ):
        customer = user_factory.create(role=Role.CUSTOMER, password="correct-password-1")
        headers = auth_headers(client, customer.email, "correct-password-1")

        response = client.post(
            "/api/tickets",
            headers=headers,
            json={
                "title": title,
                "description": description,
                "category": category.value,
                "priority": priority.value,
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "open"
        assert body["requester"]["id"] == str(customer.id)


class TestP9InvalidEnumsRejected:
    """P9 -- Validates: Requirements 3.3"""

    @given(bad_category=invalid_enum_value)
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        max_examples=20,
    )
    def test_invalid_category_rejected_and_not_persisted(
        self, client, user_factory, db_session, bad_category
    ):
        customer = user_factory.create(role=Role.CUSTOMER, password="correct-password-1")
        headers = auth_headers(client, customer.email, "correct-password-1")
        before_count = db_session.query(Ticket).count()

        response = client.post(
            "/api/tickets",
            headers=headers,
            json={
                "title": "Title",
                "description": "Description",
                "category": bad_category,
                "priority": "low",
            },
        )

        assert response.status_code == 422
        assert db_session.query(Ticket).count() == before_count

    @given(bad_priority=invalid_enum_value)
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        max_examples=20,
    )
    def test_invalid_priority_rejected_and_not_persisted(
        self, client, user_factory, db_session, bad_priority
    ):
        customer = user_factory.create(role=Role.CUSTOMER, password="correct-password-1")
        headers = auth_headers(client, customer.email, "correct-password-1")
        before_count = db_session.query(Ticket).count()

        response = client.post(
            "/api/tickets",
            headers=headers,
            json={
                "title": "Title",
                "description": "Description",
                "category": "general",
                "priority": bad_priority,
            },
        )

        assert response.status_code == 422
        assert db_session.query(Ticket).count() == before_count
