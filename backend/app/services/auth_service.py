"""
Authentication service — user registration, login, and token management.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.models import User
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse

logger = get_logger(__name__)


class AuthService:
    """Handles user authentication operations."""

    async def register(self, data: RegisterRequest, db: AsyncSession) -> UserResponse:
        """
        Register a new user.

        Raises:
            AuthenticationError: If email already exists.
        """
        # Check for existing user
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise AuthenticationError("Email already registered")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            name=data.name,
        )
        db.add(user)
        await db.flush()

        logger.info("user_registered", user_id=str(user.id), email=user.email)

        return UserResponse.model_validate(user)

    async def login(self, email: str, password: str, db: AsyncSession) -> TokenResponse:
        """
        Authenticate user and return JWT tokens.

        Raises:
            AuthenticationError: If credentials are invalid.
        """
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        logger.info("user_logged_in", user_id=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_tokens(self, refresh_token_str: str, db: AsyncSession) -> TokenResponse:
        """
        Issue new token pair from a valid refresh token.

        Raises:
            AuthenticationError: If refresh token is invalid.
        """
        user_id = verify_refresh_token(refresh_token_str)

        stmt = select(User).where(User.id == UUID(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("User not found")

        access_token = create_access_token(str(user.id))
        new_refresh = create_refresh_token(str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
        )

    async def get_user(self, user_id: UUID, db: AsyncSession) -> UserResponse:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User", str(user_id))

        return UserResponse.model_validate(user)
