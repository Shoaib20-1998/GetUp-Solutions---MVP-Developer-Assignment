"""Ticket creation tests. Scope per Requirement 15.2: valid creation, missing
required fields, and creation when the AI provider is unavailable.
"""

import io

from app.models import Activity, EventType, Role
from tests.conftest import auth_headers
from tests.stub_ai_provider import FailingAIProvider


def _customer_headers(client, user_factory):
    user = user_factory.create(role=Role.CUSTOMER, password="correct-password-1")
    return auth_headers(client, user.email, "correct-password-1"), user


class TestTicketCreationExamples:
    def test_missing_title_returns_422(self, client, user_factory):
        headers, _ = _customer_headers(client, user_factory)
        response = client.post(
            "/api/tickets",
            headers=headers,
            json={"description": "Something broke", "category": "general", "priority": "low"},
        )
        assert response.status_code == 422
        fields = {d["field"] for d in response.json()["error"]["details"]}
        assert "title" in fields

    def test_missing_description_returns_422(self, client, user_factory):
        headers, _ = _customer_headers(client, user_factory)
        response = client.post(
            "/api/tickets",
            headers=headers,
            json={"title": "Broken thing", "category": "general", "priority": "low"},
        )
        assert response.status_code == 422
        fields = {d["field"] for d in response.json()["error"]["details"]}
        assert "description" in fields

    def test_missing_both_returns_422_naming_both(self, client, user_factory):
        headers, _ = _customer_headers(client, user_factory)
        response = client.post(
            "/api/tickets",
            headers=headers,
            json={"category": "general", "priority": "low"},
        )
        assert response.status_code == 422
        fields = {d["field"] for d in response.json()["error"]["details"]}
        assert {"title", "description"} <= fields

    def test_creation_without_attachment_succeeds(self, client, user_factory):
        headers, _ = _customer_headers(client, user_factory)
        response = client.post(
            "/api/tickets",
            headers=headers,
            json={
                "title": "Broken thing",
                "description": "Details here",
                "category": "general",
                "priority": "low",
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "open"

    def test_creation_with_attachment_succeeds(self, client, user_factory):
        headers, _ = _customer_headers(client, user_factory)
        create_response = client.post(
            "/api/tickets",
            headers=headers,
            json={
                "title": "Broken thing",
                "description": "Details here",
                "category": "general",
                "priority": "low",
            },
        )
        ticket_id = create_response.json()["id"]

        upload_response = client.post(
            f"/api/tickets/{ticket_id}/attachments",
            headers=headers,
            files={"file": ("note.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert upload_response.status_code == 201
        assert upload_response.json()["filename"] == "note.txt"

    def test_attachment_at_size_limit_succeeds(self, client, user_factory):
        from app.config import get_settings

        headers, _ = _customer_headers(client, user_factory)
        ticket_id = client.post(
            "/api/tickets",
            headers=headers,
            json={
                "title": "Broken thing",
                "description": "Details here",
                "category": "general",
                "priority": "low",
            },
        ).json()["id"]

        limit = get_settings().max_attachment_bytes
        body = b"x" * limit
        response = client.post(
            f"/api/tickets/{ticket_id}/attachments",
            headers=headers,
            files={"file": ("exact.txt", io.BytesIO(body), "text/plain")},
        )
        assert response.status_code == 201

    def test_attachment_over_size_limit_returns_413(self, client, user_factory):
        from app.config import get_settings

        headers, _ = _customer_headers(client, user_factory)
        ticket_id = client.post(
            "/api/tickets",
            headers=headers,
            json={
                "title": "Broken thing",
                "description": "Details here",
                "category": "general",
                "priority": "low",
            },
        ).json()["id"]

        limit = get_settings().max_attachment_bytes
        body = b"x" * (limit + 1)
        response = client.post(
            f"/api/tickets/{ticket_id}/attachments",
            headers=headers,
            files={"file": ("too_big.txt", io.BytesIO(body), "text/plain")},
        )
        assert response.status_code == 413

    def test_disallowed_content_type_returns_415(self, client, user_factory):
        headers, _ = _customer_headers(client, user_factory)
        ticket_id = client.post(
            "/api/tickets",
            headers=headers,
            json={
                "title": "Broken thing",
                "description": "Details here",
                "category": "general",
                "priority": "low",
            },
        ).json()["id"]

        response = client.post(
            f"/api/tickets/{ticket_id}/attachments",
            headers=headers,
            files={"file": ("script.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        )
        assert response.status_code == 415

    def test_creation_writes_single_activity_entry(self, client, user_factory, db_session):
        headers, _ = _customer_headers(client, user_factory)
        ticket_id = client.post(
            "/api/tickets",
            headers=headers,
            json={
                "title": "Broken thing",
                "description": "Details here",
                "category": "general",
                "priority": "low",
            },
        ).json()["id"]

        entries = (
            db_session.query(Activity)
            .filter_by(ticket_id=ticket_id, event_type=EventType.CREATED)
            .all()
        )
        assert len(entries) == 1


class TestAiGracefulFallback:
    def test_creation_succeeds_when_ai_provider_raises(self, client, user_factory):
        """Ticket creation must succeed even when the primary AI provider is
        unavailable (Requirement 9.7/15.2). The orchestration layer retries
        once with the deterministic mock, so a suggestion is still present
        whenever possible -- creation succeeding is the actual requirement;
        this asserts that, plus the mock fallback firing."""
        from app.services import triage

        triage.set_provider(FailingAIProvider())
        headers, _ = _customer_headers(client, user_factory)

        response = client.post(
            "/api/tickets",
            headers=headers,
            json={
                "title": "Broken thing",
                "description": "Details here",
                "category": "general",
                "priority": "low",
            },
        )
        assert response.status_code == 201
        body = response.json()
        # The mock fallback fires and produces a real (mock) suggestion.
        assert body["ai_suggested_category"] is not None
        assert body["ai_suggested_priority"] is not None
