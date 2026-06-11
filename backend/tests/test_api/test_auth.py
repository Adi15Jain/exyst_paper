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
async def test_login_rate_limit_trips(client: AsyncClient):
    """After enough rapid attempts from one IP, login returns 429."""
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
