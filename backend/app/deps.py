"""Shared request dependencies: who is calling, and may they.

`HTTPBearer` is configured with ``auto_error=False`` on purpose. Its default
behaviour answers a *missing* Authorization header with 403, whereas
Requirement 1.6 asks for 401 on an absent, expired, or badly signed token. With
auto_error off, this module owns the distinction: 401 means "we do not know who
you are", 403 means "we know, and you may not".
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.enums import Role
from app.services.auth import TokenError, decode_access_token

bearer_scheme = HTTPBearer(auto_error=False, description="JWT from /api/auth/login")

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise _UNAUTHENTICATED

    try:
        claims = decode_access_token(credentials.credentials)
    except TokenError:
        raise _UNAUTHENTICATED from None

    user = db.get(User, claims.user_id)
    if user is None:
        # Token is well formed but the subject no longer exists.
        raise _UNAUTHENTICATED
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*allowed: Role) -> Callable[[User], User]:
    """Dependency factory asserting the caller holds one of ``allowed``."""

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role may not perform this action",
            )
        return user

    return dependency
