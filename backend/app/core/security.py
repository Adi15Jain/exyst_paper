"""
JWT authentication utilities.

Handles token creation, validation, and password hashing.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config import get_settings
from app.core.exceptions import InvalidTokenError


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        subject: The user ID (stored as 'sub' claim).
        extra_claims: Additional claims to include in the token.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
        **(extra_claims or {}),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, token_version: int = 0) -> str:
    """
    Create a long-lived JWT refresh token.

    Args:
        subject: The user ID (stored as 'sub' claim).
        token_version: The user's current token version ('ver' claim). Tokens
            whose version no longer matches the user's are rejected, which is
            how logout revokes all outstanding refresh tokens.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "refresh",
        "ver": token_version,
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _password_fingerprint(hashed_password: str) -> str:
    """
    Short digest of the current password hash.

    Embedded in reset tokens so a token stops working the moment the password
    changes — that makes a reset link single-use without any server-side state.
    """
    return hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()[:16]


def create_password_reset_token(subject: str, hashed_password: str) -> str:
    """Create a short-lived, single-use password reset token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "password_reset",
        "pwf": _password_fingerprint(hashed_password),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_password_reset_token(token: str, hashed_password: str) -> str:
    """
    Verify a password reset token against the user's *current* password hash
    and return the user ID.

    Raises:
        InvalidTokenError: If invalid, expired, the wrong token type, or
            already used (the password has changed since it was issued).
    """
    payload = decode_token(token)

    if payload.get("type") != "password_reset":
        raise InvalidTokenError("Not a password reset token")

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("Token missing subject")

    if payload.get("pwf") != _password_fingerprint(hashed_password):
        raise InvalidTokenError("This reset link has already been used")

    return user_id


def decode_token(token: str) -> dict[str, Any]:
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


def verify_refresh_token(token: str) -> tuple[str, int]:
    """
    Verify a refresh token and return (user_id, token_version).

    Tokens minted before versioning existed carry no 'ver' claim and are
    treated as version 0.

    Raises:
        InvalidTokenError: If invalid, expired, or wrong token type.
    """
    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise InvalidTokenError("Not a refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("Token missing subject")

    return user_id, int(payload.get("ver", 0))
