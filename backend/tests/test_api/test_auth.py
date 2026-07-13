"""
Authentication endpoint tests.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_register_endpoint(client: AsyncClient):
    random_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": random_email, "password": "password123", "name": "Test User"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == random_email
    assert "id" in body
    assert "hashed_password" not in body  # never leak the hash


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client: AsyncClient):
    auth = await register_and_login(client)
    dup = await client.post(
        "/api/v1/auth/register",
        json={"email": auth["email"], "password": "password123", "name": "Dupe"},
    )
    assert dup.status_code == 401


@pytest.mark.asyncio
async def test_register_short_password_rejected(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": f"u_{uuid.uuid4().hex[:8]}@example.com", "password": "short", "name": "X"},
    )
    assert response.status_code == 422  # pydantic min_length validation


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    auth = await register_and_login(client)
    assert auth["access_token"]
    assert auth["refresh_token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    auth = await register_and_login(client)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": auth["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": f"nobody_{uuid.uuid4().hex[:8]}@example.com", "password": "password123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client: AsyncClient):
    auth = await register_and_login(client)
    response = await client.get("/api/v1/auth/me", headers=auth["headers"])
    assert response.status_code == 200
    assert response.json()["email"] == auth["email"]


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_rejects_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client: AsyncClient):
    auth = await register_and_login(client)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": auth["refresh_token"]},
    )
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"]
    # The new access token must actually authenticate.
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client: AsyncClient):
    """An access token must not be usable as a refresh token."""
    auth = await register_and_login(client)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": auth["access_token"]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_via_cookie(client: AsyncClient):
    """Browsers refresh with the httpOnly cookie alone; no token in the body."""
    await register_and_login(client)  # login response sets the cookie in the jar
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    # Cookie-based callers must NOT receive the refresh token in the body.
    assert body["refresh_token"] is None
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_refresh_without_any_token(client: AsyncClient):
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_tokens(client: AsyncClient):
    auth = await register_and_login(client)
    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    # The pre-logout refresh token must now be rejected (version bumped).
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": auth["refresh_token"]},
    )
    assert response.status_code == 401
    # And the cookie was cleared, so a bare refresh fails too.
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_is_idempotent(client: AsyncClient):
    await register_and_login(client)
    first = await client.post("/api/v1/auth/logout")
    second = await client.post("/api/v1/auth/logout")
    assert first.status_code == 204
    assert second.status_code == 204


@pytest.mark.asyncio
async def test_login_after_logout_issues_valid_tokens(client: AsyncClient):
    """Logout must not lock the account out — a fresh login works again."""
    auth = await register_and_login(client)
    await client.post("/api/v1/auth/logout")
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": auth["email"], "password": auth["password"]},
    )
    assert login.status_code == 200
    new_refresh = login.json()["refresh_token"]
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert response.status_code == 200


# --- Profile / account management ---


@pytest.mark.asyncio
async def test_update_profile_name(client: AsyncClient):
    auth = await register_and_login(client)
    resp = await client.patch(
        "/api/v1/auth/me",
        headers=auth["headers"],
        json={"name": "Renamed User"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed User"


@pytest.mark.asyncio
async def test_change_password_requires_current_password(client: AsyncClient):
    auth = await register_and_login(client)
    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=auth["headers"],
        json={"current_password": "wrong-password", "new_password": "brand-new-pass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_updates_credentials_and_revokes_sessions(client: AsyncClient):
    auth = await register_and_login(client)
    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=auth["headers"],
        json={"current_password": auth["password"], "new_password": "brand-new-pass"},
    )
    assert resp.status_code == 204

    # Old refresh token is revoked (token_version bumped).
    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": auth["refresh_token"]},
    )
    assert refreshed.status_code == 401

    # Old password no longer works; the new one does.
    old = await client.post(
        "/api/v1/auth/login",
        json={"email": auth["email"], "password": auth["password"]},
    )
    assert old.status_code == 401

    new = await client.post(
        "/api/v1/auth/login",
        json={"email": auth["email"], "password": "brand-new-pass"},
    )
    assert new.status_code == 200


@pytest.mark.asyncio
async def test_delete_account(client: AsyncClient):
    auth = await register_and_login(client)
    resp = await client.delete("/api/v1/auth/me", headers=auth["headers"])
    assert resp.status_code == 204

    # The account is gone: its token no longer resolves, and login fails.
    me = await client.get("/api/v1/auth/me", headers=auth["headers"])
    assert me.status_code == 404

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": auth["email"], "password": auth["password"]},
    )
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_removes_documents(client: AsyncClient):
    """Deleting an account must cascade to its documents (FK would block otherwise)."""
    auth = await register_and_login(client)
    up = await client.post(
        "/api/v1/documents/upload",
        headers=auth["headers"],
        files={"file": ("exam.pdf", b"%PDF-1.4\nfake\n%%EOF", "application/pdf")},
    )
    assert up.status_code == 201

    resp = await client.delete("/api/v1/auth/me", headers=auth["headers"])
    assert resp.status_code == 204


# --- Password reset ---


@pytest.mark.asyncio
async def test_forgot_password_does_not_reveal_whether_email_exists(client: AsyncClient):
    """Both a known and an unknown address must return the same 202."""
    auth = await register_and_login(client)

    known = await client.post(
        "/api/v1/auth/forgot-password", json={"email": auth["email"]}
    )
    unknown = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": f"nobody_{uuid.uuid4().hex[:8]}@example.com"},
    )

    assert known.status_code == 202
    assert unknown.status_code == 202
    assert known.json() == unknown.json()


@pytest.mark.asyncio
async def test_reset_password_flow(client: AsyncClient):
    from sqlalchemy import select

    from app.core.security import create_password_reset_token
    from app.db.session import async_session_factory
    from app.models import User

    auth = await register_and_login(client)

    # Mint the token the way the emailed link would.
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == auth["email"]))
        user = result.scalar_one()
        token = create_password_reset_token(str(user.id), user.hashed_password)

    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "reset-password-1"},
    )
    assert resp.status_code == 204

    # New password works, old one doesn't.
    new = await client.post(
        "/api/v1/auth/login",
        json={"email": auth["email"], "password": "reset-password-1"},
    )
    assert new.status_code == 200

    old = await client.post(
        "/api/v1/auth/login",
        json={"email": auth["email"], "password": auth["password"]},
    )
    assert old.status_code == 401

    # The link is single-use: replaying it fails now the password has changed.
    replay = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "another-password"},
    )
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_rejects_garbage_token(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "whatever-123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_rejects_access_token(client: AsyncClient):
    """An access token must not be usable as a reset token."""
    auth = await register_and_login(client)
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": auth["access_token"], "new_password": "whatever-123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limit_trips(client: AsyncClient):
    """
    After enough rapid attempts from one IP, login returns 429.

    This also pins down a subtlety in the Postgres-backed limiter: a *failed*
    login raises 401, which rolls back the request's DB transaction. The counter
    therefore has to be written on its own session — otherwise every failed
    attempt would roll back its own increment and brute-force limiting would
    never trip at all.
    """
    auth = await register_and_login(client)
    saw_429 = False
    # login limit is 10/min; loop past it.
    for _ in range(15):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": auth["email"], "password": "wrong-password"},
        )
        if resp.status_code == 429:
            saw_429 = True
            break
    assert saw_429
