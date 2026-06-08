"""
FastAPI dependencies — authentication, database session, etc.
"""

from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AuthenticationError, InvalidTokenError
from app.core.security import verify_access_token

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> UUID:
    """
    Extract and validate user ID from JWT token.

    Usage:
        @router.get("/protected")
        async def protected(user_id: UUID = Depends(get_current_user_id)):
            ...
    """
    if not credentials:
        raise AuthenticationError("Authorization header required")

    try:
        user_id_str = verify_access_token(credentials.credentials)
        return UUID(user_id_str)
    except InvalidTokenError:
        raise
    except Exception as e:
        raise AuthenticationError(f"Invalid authorization: {str(e)}")


async def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> UUID | None:
    """
    Optionally extract user ID — returns None if no token provided.
    Useful for endpoints that work both authenticated and unauthenticated.
    """
    if not credentials:
        return None

    try:
        user_id_str = verify_access_token(credentials.credentials)
        return UUID(user_id_str)
    except Exception:
        return None
