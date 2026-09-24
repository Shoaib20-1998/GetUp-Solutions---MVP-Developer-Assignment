"""Property-based tests for authentication. See design.md's Correctness
Properties section (P1, P2, P3).
"""

from datetime import UTC, datetime

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.models import Role
from app.services.auth import create_access_token, decode_access_token, hash_password, verify_password

# Constrained to the valid input space: printable, non-whitespace-only text
# for the password (matching what the registration schema actually accepts),
# and a password long enough to satisfy the 8-character minimum.
password_strategy = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=8, max_size=72
)


class TestP1CredentialsNeverPlaintext:
    """P1 -- Validates: Requirements 1.1

    bcrypt is deliberately slow (that's the point of it), so example count is
    capped here: the property is about the hash/verify contract, not about
    exercising bcrypt's own internals across hundreds of inputs.
    """

    @given(password=password_strategy)
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        max_examples=15,
    )
    def test_hash_differs_and_verifies(self, password):
        password_hash = hash_password(password)
        assert password_hash != password
        assert verify_password(password, password_hash)

    @given(password=password_strategy, other_password=password_strategy)
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        max_examples=15,
    )
    def test_wrong_password_does_not_verify(self, password, other_password):
        if password == other_password:
            return
        password_hash = hash_password(password)
        assert not verify_password(other_password, password_hash)


class TestP2LoginRoundTripsIdentity:
    """P2 -- Validates: Requirements 1.4"""

    @given(role=st.sampled_from(list(Role)))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_token_round_trips_identity(self, role, user_factory):
        user = user_factory.create(role=role)
        token = create_access_token(user.id, user.role)
        claims = decode_access_token(token)

        assert claims.user_id == user.id
        assert claims.role == role
        assert claims.expires_at > datetime.now(UTC)


class TestP3FailedLoginIndistinguishable:
    """P3 -- Validates: Requirements 1.5"""

    @given(
        registered_local=st.uuids(),
        unregistered_local=st.uuids(),
        wrong_password=password_strategy,
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
        max_examples=15,
    )
    def test_wrong_password_and_unknown_email_match(
        self, client, registered_local, unregistered_local, wrong_password
    ):
        if registered_local == unregistered_local:
            return

        registered_email = f"{registered_local}@example.com"
        unregistered_email = f"{unregistered_local}@example.com"

        client.post(
            "/api/auth/register",
            json={
                "email": registered_email,
                "password": "correct-password-1",
                "full_name": "Jamie Test",
            },
        )
        if wrong_password == "correct-password-1":
            return

        wrong_password_response = client.post(
            "/api/auth/login",
            json={"email": registered_email, "password": wrong_password},
        )
        unknown_email_response = client.post(
            "/api/auth/login",
            json={"email": unregistered_email, "password": wrong_password},
        )

        assert wrong_password_response.status_code == 401
        assert unknown_email_response.status_code == 401
        assert wrong_password_response.json() == unknown_email_response.json()
