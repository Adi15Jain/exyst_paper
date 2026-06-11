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
