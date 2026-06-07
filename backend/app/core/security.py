"""
JWT authentication utilities.

Handles token creation, validation, and password hashing.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.core.exceptions import InvalidTokenError

# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        subject: The user ID (stored as 'sub' claim).
        extra_claims: Additional claims to include in the token.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
        **(extra_claims or {}),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """
    Create a long-lived JWT refresh token.

    Args:
        subject: The user ID (stored as 'sub' claim).
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string.

    Returns:
        The decoded payload dict.

    Raises:
        InvalidTokenError: If the token is invalid or expired.
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")


def verify_access_token(token: str) -> str:
    """
    Verify an access token and return the user ID.

    Raises:
        InvalidTokenError: If invalid, expired, or wrong token type.
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise InvalidTokenError("Not an access token")

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("Token missing subject")

    return user_id


def verify_refresh_token(token: str) -> str:
    """
    Verify a refresh token and return the user ID.

    Raises:
        InvalidTokenError: If invalid, expired, or wrong token type.
    """
    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise InvalidTokenError("Not a refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("Token missing subject")

    return user_id
