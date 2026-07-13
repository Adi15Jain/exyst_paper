"""
Authentication endpoints.

The refresh token is delivered to browsers via an httpOnly cookie so script
(XSS) can never read it; SameSite=Lax keeps cross-site POSTs from sending it.
Non-browser API clients may instead pass the refresh token in the request
body, in which case the rotated token is returned in the body too.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

auth_service = AuthService()

# Per-IP brute-force friction on credential endpoints.
login_rate_limit = rate_limit("login", max_requests=10, window_seconds=60)
register_rate_limit = rate_limit("register", max_requests=5, window_seconds=60)
# Reset endpoints send mail / attempt credential changes — keep them tight.
forgot_password_rate_limit = rate_limit("forgot_password", max_requests=5, window_seconds=900)
reset_password_rate_limit = rate_limit("reset_password", max_requests=10, window_seconds=900)

REFRESH_COOKIE_NAME = "exyst_refresh_token"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Store the refresh token in an httpOnly cookie."""
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        # Browsers treat localhost as trustworthy, but Safari still drops
        # Secure cookies over plain http — relax only in DEBUG.
        secure=not settings.DEBUG,
        samesite="lax",
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/",
    )


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
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Authenticate and receive JWT tokens (refresh token also set as an httpOnly cookie)."""
    tokens = await auth_service.login(data.email, data.password, db)
    assert tokens.refresh_token is not None
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    data: RefreshTokenRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get new tokens using a refresh token.

    Browser clients send it automatically via the httpOnly cookie; API clients
    may pass it in the body. The rotated refresh token is returned in the body
    only for body-based callers — cookie callers get it via Set-Cookie alone.
    """
    from_body = data.refresh_token if data else None
    token = from_body or request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise AuthenticationError("Missing refresh token")

    tokens = await auth_service.refresh_tokens(token, db)
    assert tokens.refresh_token is not None
    _set_refresh_cookie(response, tokens.refresh_token)

    if from_body:
        return tokens
    return TokenResponse(access_token=tokens.access_token, refresh_token=None)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    data: RefreshTokenRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Log out: revoke all outstanding refresh tokens and clear the cookie.

    Idempotent — succeeds even if the token is missing, invalid, or already
    revoked, so clients can always call it safely.
    """
    token = (data.refresh_token if data else None) or request.cookies.get(REFRESH_COOKIE_NAME)
    if token:
        await auth_service.logout(token, db)
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the current authenticated user's profile."""
    return await auth_service.get_user(user_id, db)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: UpdateProfileRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's display name."""
    return await auth_service.update_profile(user_id, data.name, db)


@router.delete("/me", status_code=204)
async def delete_account(
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete the account and all of its documents and results."""
    await auth_service.delete_account(user_id, db)
    _clear_refresh_cookie(response)


@router.post("/change-password", status_code=204)
async def change_password(
    data: ChangePasswordRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Change the password of the signed-in user.

    Requires the current password and revokes all refresh tokens, so other
    devices are signed out. The caller's access token stays valid until it
    expires; the client is expected to re-authenticate.
    """
    await auth_service.change_password(
        user_id, data.current_password, data.new_password, db
    )


@router.post(
    "/forgot-password",
    status_code=202,
    dependencies=[Depends(forgot_password_rate_limit)],
)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Email a password reset link.

    Always returns 202, whether or not the address has an account — telling
    the caller which emails are registered would be an enumeration oracle.
    """
    await auth_service.request_password_reset(data.email, db)
    return {"message": "If that email has an account, a reset link is on its way."}


@router.post(
    "/reset-password",
    status_code=204,
    dependencies=[Depends(reset_password_rate_limit)],
)
async def reset_password(
    data: ResetPasswordRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Set a new password using the token from the reset email.

    The link is single-use (it stops working once the password changes) and
    resetting revokes every existing session.
    """
    await auth_service.reset_password(data.token, data.new_password, db)
    _clear_refresh_cookie(response)
