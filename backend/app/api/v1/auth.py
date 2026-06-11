"""
Authentication endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

auth_service = AuthService()

# Per-IP brute-force friction on credential endpoints.
login_rate_limit = rate_limit("login", max_requests=10, window_seconds=60)
register_rate_limit = rate_limit("register", max_requests=5, window_seconds=60)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(register_rate_limit)],
)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    return await auth_service.register(data, db)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(login_rate_limit)],
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and receive JWT tokens."""
    return await auth_service.login(data.email, data.password, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Get new tokens using a refresh token."""
    return await auth_service.refresh_tokens(data.refresh_token, db)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the current authenticated user's profile."""
    return await auth_service.get_user(user_id, db)
