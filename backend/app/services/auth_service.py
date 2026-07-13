"""
Authentication service — user registration, login, and token management.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.exceptions import AuthenticationError, InvalidTokenError, NotFoundError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    verify_password_reset_token,
    verify_refresh_token,
)
from app.models import User
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from app.services.email import send_password_reset

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
        refresh_token = create_refresh_token(str(user.id), user.token_version)

        logger.info("user_logged_in", user_id=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_tokens(self, refresh_token_str: str, db: AsyncSession) -> TokenResponse:
        """
        Issue new token pair from a valid refresh token.

        Raises:
            AuthenticationError: If the refresh token is invalid or has been
                revoked (its version no longer matches the user's).
        """
        user_id, token_version = verify_refresh_token(refresh_token_str)

        stmt = select(User).where(User.id == UUID(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("User not found")

        if token_version != user.token_version:
            raise AuthenticationError("Refresh token has been revoked")

        access_token = create_access_token(str(user.id))
        new_refresh = create_refresh_token(str(user.id), user.token_version)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
        )

    async def logout(self, refresh_token_str: str, db: AsyncSession) -> None:
        """
        Revoke all of a user's outstanding refresh tokens.

        Bumps the user's token_version so every previously issued refresh
        token fails version validation. Idempotent: an invalid or already
        revoked token is a no-op, so logout never errors for the client.
        """
        try:
            user_id, _ = verify_refresh_token(refresh_token_str)
        except Exception:
            return

        stmt = select(User).where(User.id == UUID(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.token_version += 1
            await db.flush()
            logger.info("user_logged_out", user_id=str(user.id))

    async def get_user(self, user_id: UUID, db: AsyncSession) -> UserResponse:
        """Get user by ID."""
        user = await self._require_user(user_id, db)
        return UserResponse.model_validate(user)

    async def _require_user(self, user_id: UUID, db: AsyncSession) -> User:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User", str(user_id))

        return user

    async def update_profile(
        self, user_id: UUID, name: str, db: AsyncSession
    ) -> UserResponse:
        """Update the current user's display name."""
        user = await self._require_user(user_id, db)
        user.name = name.strip()
        await db.flush()
        return UserResponse.model_validate(user)

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        db: AsyncSession,
    ) -> None:
        """
        Change the password of a signed-in user.

        Requires the current password (so a stolen access token alone can't
        take over the account) and revokes every existing refresh token, since
        a password change should sign other devices out.

        Raises:
            AuthenticationError: If the current password is wrong.
        """
        user = await self._require_user(user_id, db)

        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")

        user.hashed_password = hash_password(new_password)
        user.token_version += 1
        await db.flush()

        logger.info("password_changed", user_id=str(user.id))

    async def delete_account(self, user_id: UUID, db: AsyncSession) -> None:
        """
        Permanently delete the user and everything they own.

        Documents, analyses, predictions, and vector chunks go with them via
        the ORM/FK cascades; stored files are removed best-effort.
        """
        from app.models import Analysis, Document
        from app.services.storage import delete_stored_file

        user = await self._require_user(user_id, db)

        # Collect file paths before the rows disappear.
        docs_result = await db.execute(
            select(Document).where(Document.user_id == user_id)
        )
        file_paths = [d.file_path for d in docs_result.scalars().all()]

        # Eager-load the tree so the cascade doesn't lazy-load under asyncio.
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.documents)
                .selectinload(Document.analyses)
                .selectinload(Analysis.predictions)
            )
        )
        result = await db.execute(stmt)
        user = result.scalar_one()

        await db.delete(user)
        await db.flush()

        for path in file_paths:
            await delete_stored_file(path)

        logger.info("account_deleted", user_id=str(user_id), documents=len(file_paths))

    async def request_password_reset(self, email: str, db: AsyncSession) -> None:
        """
        Email a password reset link.

        Deliberately silent about whether the address exists — otherwise this
        endpoint becomes an account-enumeration oracle. Callers always return
        the same response.
        """
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.info("password_reset_requested_unknown_email")
            return

        settings = get_settings()
        token = create_password_reset_token(str(user.id), user.hashed_password)
        reset_url = f"{settings.APP_BASE_URL.rstrip('/')}/reset-password?token={token}"

        await send_password_reset(to=user.email, name=user.name, reset_url=reset_url)
        logger.info("password_reset_requested", user_id=str(user.id))

    async def reset_password(
        self, token: str, new_password: str, db: AsyncSession
    ) -> None:
        """
        Set a new password from a reset token.

        The token is bound to the password it was issued against, so it stops
        working as soon as the password changes (single use). Resetting also
        revokes all existing sessions.

        Raises:
            InvalidTokenError: If the token is invalid, expired, or used.
        """
        # The token carries the user id, but validating it needs that user's
        # current password hash — so decode first, then re-verify properly.
        unverified = decode_token(token)
        user_id = unverified.get("sub")
        if not user_id:
            raise InvalidTokenError("Token missing subject")

        user = await self._require_user(UUID(user_id), db)

        verify_password_reset_token(token, user.hashed_password)

        user.hashed_password = hash_password(new_password)
        user.token_version += 1
        await db.flush()

        logger.info("password_reset_completed", user_id=str(user.id))
