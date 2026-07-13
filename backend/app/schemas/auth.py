"""
Authentication schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
    JWT token response.

    refresh_token is populated only when the client supplied its refresh token
    in the request body (non-browser API clients). Browser clients receive the
    refresh token exclusively via an httpOnly cookie, so an XSS payload that
    calls /auth/refresh cannot read a long-lived credential from the response.
    """
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class UserResponse(BaseModel):
    """User data response."""
    id: UUID
    email: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    """Change the current user's display name."""
    name: str = Field(min_length=1, max_length=255)


class ChangePasswordRequest(BaseModel):
    """Change password while signed in (requires the current password)."""
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    """Request a password reset link."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Set a new password using a reset token from the emailed link."""
    token: str
    new_password: str = Field(min_length=8, max_length=128)
