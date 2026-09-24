"""Property-based tests for role-scoped ticket visibility. See design.md's
Correctness Properties section (P4, P5, P6, P7).
"""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.models import Role
from tests.conftest import auth_headers

PASSWORD = "correct-password-1"

# Small population sizes keep each Hypothesis example's DB work bounded
# while still exercising arbitrary requester/assignee distributions. Login
# does real bcrypt work per user in the population, which dominates runtime,
# so both the population size and the example count stay deliberately small.
population_strategy = st.lists(
    st.tuples(st.integers(min_value=0, max_value=2), st.integers(min_value=-1, max_value=1)),
    min_size=1,
    max_size=4,
)


def _reset_tables(db_session):
    """Hypothesis runs many examples per test *invocation*, all sharing the
    same function-scoped db_session/transaction (rollback only happens
    between pytest tests, not between examples). Without this, tickets and
    users from earlier examples in the same run would still be visible to
    later examples, corrupting the "list equals exactly this population"
    assertion. Explicit per-example cleanup keeps each example isolated."""
    from app.models import Activity, Attachment, Comment, Ticket, User

    db_session.query(Activity).delete()
    db_session.query(Attachment).delete()
    db_session.query(Comment).delete()
    db_session.query(Ticket).delete()
    db_session.query(User).delete()
    db_session.commit()


def _build_population(client, db_session, user_factory, ticket_factory, plan):
    """plan: list of (customer_index, assignee_index) pairs. assignee_index
    of -1 means unassigned; 0/1 map into a fixed pool of two agents."""
    _reset_tables(db_session)

    customers = [
        user_factory.create(role=Role.CUSTOMER, password=PASSWORD) for _ in range(3)
    ]
    agents = [user_factory.create(role=Role.AGENT, password=PASSWORD) for _ in range(2)]

    tickets = []
    for customer_idx, assignee_idx in plan:
        requester = customers[customer_idx]
        assignee = agents[assignee_idx] if assignee_idx >= 0 else None
        tickets.append(ticket_factory.create(requester=requester, assignee=assignee))

    return customers, agents, tickets


def _list_ticket_ids(client, headers):
    response = client.get("/api/tickets?page_size=100", headers=headers)
    assert response.status_code == 200
    return {item["id"] for item in response.json()["items"]}


class TestP4CustomerSeesOnlyOwnTickets:
    """P4 -- Validates: Requirements 2.3"""

    @given(plan=population_strategy)
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        max_examples=8,
    )
    def test_customer_list_equals_own_tickets(
        self, client, db_session, user_factory, ticket_factory, plan
    ):
        customers, _, tickets = _build_population(
            client, db_session, user_factory, ticket_factory, plan
        )

        for idx, customer in enumerate(customers):
            headers = auth_headers(client, customer.email, PASSWORD)
            visible_ids = _list_ticket_ids(client, headers)
            expected_ids = {
                str(t.id) for t, (c_idx, _) in zip(tickets, plan) if c_idx == idx
            }
            assert visible_ids == expected_ids


class TestP5AgentSeesOnlyAssignedTickets:
    """P5 -- Validates: Requirements 2.4"""

    @given(plan=population_strategy)
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        max_examples=8,
    )
    def test_agent_list_equals_assigned_tickets(
        self, client, db_session, user_factory, ticket_factory, plan
    ):
        _, agents, tickets = _build_population(
            client, db_session, user_factory, ticket_factory, plan
        )

        for idx, agent in enumerate(agents):
            headers = auth_headers(client, agent.email, PASSWORD)
            visible_ids = _list_ticket_ids(client, headers)
            expected_ids = {
                str(t.id) for t, (_, a_idx) in zip(tickets, plan) if a_idx == idx
            }
            assert visible_ids == expected_ids


class TestP6AdminSeesFullSet:
    """P6 -- Validates: Requirements 2.5"""

    @given(plan=population_strategy)
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        max_examples=8,
    )
    def test_admin_list_equals_every_ticket(
        self, client, db_session, user_factory, ticket_factory, plan
    ):
        _, _, tickets = _build_population(client, db_session, user_factory, ticket_factory, plan)
        admin = user_factory.create(role=Role.ADMIN, password=PASSWORD)

        headers = auth_headers(client, admin.email, PASSWORD)
        visible_ids = _list_ticket_ids(client, headers)
        assert visible_ids == {str(t.id) for t in tickets}


class TestP7UnentitledAccessIsAbsence:
    """P7 -- Validates: Requirements 2.6"""

    @given(viewer_role=st.sampled_from([Role.CUSTOMER, Role.AGENT]))
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        max_examples=10,
    )
    def test_unentitled_fetch_returns_404_never_403(
        self, client, db_session, user_factory, ticket_factory, viewer_role
    ):
        _reset_tables(db_session)
        owner = user_factory.create(role=Role.CUSTOMER, password=PASSWORD)
        other_agent = user_factory.create(role=Role.AGENT, password=PASSWORD)
        ticket = ticket_factory.create(requester=owner, assignee=other_agent)

        # A viewer with no relationship to this ticket at all.
        viewer = user_factory.create(role=viewer_role, password=PASSWORD)
        headers = auth_headers(client, viewer.email, PASSWORD)

        response = client.get(f"/api/tickets/{ticket.id}", headers=headers)
        assert response.status_code == 404
