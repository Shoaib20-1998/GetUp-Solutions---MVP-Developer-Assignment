"""Password hashing and JWT issue/decode.

bcrypt silently ignores anything past the 72nd byte of input, so passwords are
SHA-256 pre-hashed and base64-encoded first. That keeps the effective input a
fixed 44 bytes, which means a long password is never truncated and no arbitrary
length ceiling has to be imposed at the schema layer.
"""

import base64
import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.models.enums import Role


class TokenError(Exception):
    """Raised when a token is absent, expired, malformed, or wrongly signed."""


class TokenClaims:
    __slots__ = ("user_id", "role", "expires_at")

    def __init__(self, user_id: uuid.UUID, role: Role, expires_at: datetime) -> None:
        self.user_id = user_id
        self.role = role
        self.expires_at = expires_at


def _prepare(password: str) -> bytes:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("utf-8"))
    except ValueError:
        # Stored value is not a valid bcrypt hash.
        return False


def create_access_token(user_id: uuid.UUID, role: Role) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "role": role.value,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expiry_minutes)).timestamp()),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return TokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            role=Role(payload["role"]),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    except (JWTError, KeyError, ValueError) as exc:
        raise TokenError(str(exc)) from exc
