"""Role-based access tests. Scope per Requirement 15.3: visibility scoping,
refusal of the assignment and dashboard endpoints to non-admins, and internal
note redaction.
"""

import pytest

from app.models import Role
from tests.conftest import auth_headers

PASSWORD = "correct-password-1"


def _login(client, user_factory, role):
    user = user_factory.create(role=role, password=PASSWORD)
    return user, auth_headers(client, user.email, PASSWORD)


class TestNonAdminRefusals:
    @pytest.mark.parametrize("role", [Role.CUSTOMER, Role.AGENT])
    def test_non_admin_refused_assignment_endpoint(self, client, user_factory, ticket_factory, role):
        customer_for_ticket, _ = _login(client, user_factory, Role.CUSTOMER)
        ticket = ticket_factory.create(requester=customer_for_ticket)

        _, headers = _login(client, user_factory, role)
        agent, _ = _login(client, user_factory, Role.AGENT)

        response = client.patch(
            f"/api/tickets/{ticket.id}/assignee",
            headers=headers,
            json={"assignee_id": str(agent.id)},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize("role", [Role.CUSTOMER, Role.AGENT])
    def test_non_admin_refused_dashboard_endpoint(self, client, user_factory, role):
        _, headers = _login(client, user_factory, role)
        response = client.get("/api/dashboard", headers=headers)
        assert response.status_code == 403


class TestRegistrationRoleIgnored:
    def test_role_admin_in_payload_produces_customer(self, client, db_session):
        import uuid

        from app.models import User

        email = f"{uuid.uuid4()}@example.com"
        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": PASSWORD,
                "full_name": "Sneaky User",
                "role": "admin",
            },
        )
        assert response.status_code == 201
        created = db_session.query(User).filter_by(email=email.lower()).one()
        assert created.role is Role.CUSTOMER


class TestInternalNoteRedaction:
    def test_internal_note_absent_from_customer_view(self, client, user_factory, ticket_factory):
        customer, customer_headers = _login(client, user_factory, Role.CUSTOMER)
        agent, agent_headers = _login(client, user_factory, Role.AGENT)
        ticket = ticket_factory.create(requester=customer, assignee=agent)

        client.post(
            f"/api/tickets/{ticket.id}/comments",
            headers=agent_headers,
            json={"body": "Internal-only detail", "is_internal": True},
        )
        client.post(
            f"/api/tickets/{ticket.id}/comments",
            headers=agent_headers,
            json={"body": "Visible reply", "is_internal": False},
        )

        customer_view = client.get(f"/api/tickets/{ticket.id}/comments", headers=customer_headers)
        assert customer_view.status_code == 200
        bodies = [c["body"] for c in customer_view.json()]
        assert "Internal-only detail" not in bodies
        assert "Visible reply" in bodies

        agent_view = client.get(f"/api/tickets/{ticket.id}/comments", headers=agent_headers)
        agent_bodies = [c["body"] for c in agent_view.json()]
        assert "Internal-only detail" in agent_bodies
