"""Authentication tests. Scope per Requirement 15.1: registration, duplicate
email, login success/failure, and token rejection.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.config import get_settings
from app.models import Role

VALID_PASSWORD = "correct-password-1"


def _register_payload(**overrides) -> dict:
    # example.com is a real, reserved-for-documentation domain that the
    # email-validator library accepts; example.test does not, since .test
    # is a special-use TLD it treats as undeliverable.
    payload = {
        "email": f"{uuid.uuid4()}@example.com",
        "password": VALID_PASSWORD,
        "full_name": "Jamie Test",
    }
    payload.update(overrides)
    return payload


class TestRegistrationExamples:
    def test_duplicate_email_returns_409(self, client):
        payload = _register_payload()
        first = client.post("/api/auth/register", json=payload)
        assert first.status_code == 201

        second = client.post("/api/auth/register", json=payload)
        assert second.status_code == 409

    @pytest.mark.parametrize(
        "password,expected_status",
        [
            ("short12", 422),  # 7 characters: below the boundary
            ("longer12", 201),  # 8 characters: exactly at the boundary
        ],
    )
    def test_password_length_boundary(self, client, password, expected_status):
        response = client.post(
            "/api/auth/register", json=_register_payload(password=password)
        )
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "email",
        [
            "not-an-email",
            "missing-domain@",
            "@missing-local.com",
            "spaces in@example.com",
            "double@@example.com",
        ],
    )
    def test_malformed_email_returns_422(self, client, email):
        response = client.post("/api/auth/register", json=_register_payload(email=email))
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert any(d["field"] == "email" for d in body["error"]["details"])

    def test_supplied_role_is_ignored(self, client, db_session):
        from app.models import User

        payload = _register_payload()
        payload["role"] = "admin"
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 201

        created = db_session.query(User).filter_by(email=payload["email"].lower()).one()
        assert created.role is Role.CUSTOMER


class TestLoginExamples:
    def test_login_with_correct_credentials_returns_token(self, client):
        payload = _register_payload()
        client.post("/api/auth/register", json=payload)

        response = client.post(
            "/api/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_with_wrong_password_returns_401(self, client):
        payload = _register_payload()
        client.post("/api/auth/register", json=payload)

        response = client.post(
            "/api/auth/login", json={"email": payload["email"], "password": "wrong-password"}
        )
        assert response.status_code == 401

    def test_login_with_unknown_email_returns_401(self, client):
        response = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "whatever12"},
        )
        assert response.status_code == 401


class TestTokenRejection:
    def test_absent_token_returns_401(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_expired_token_returns_401(self, client, user_factory):
        user = user_factory.create()
        settings = get_settings()
        expired_claims = {
            "sub": str(user.id),
            "role": user.role.value,
            "iat": int((datetime.now(UTC) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(expired_claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_wrong_signature_returns_401(self, client, user_factory):
        user = user_factory.create()
        settings = get_settings()
        claims = {
            "sub": str(user.id),
            "role": user.role.value,
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(claims, "a-completely-different-secret", algorithm=settings.jwt_algorithm)

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_malformed_token_returns_401(self, client):
        response = client.get(
            "/api/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"}
        )
        assert response.status_code == 401
