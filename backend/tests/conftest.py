"""
Test fixtures and configuration.
"""

import asyncio
import uuid
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema() -> AsyncGenerator[None, None]:
    """
    Create all database tables once for the test session, then drop them.

    The app only creates tables in its FastAPI lifespan startup handler, but the
    httpx ASGITransport used by the `client` fixture does not run lifespan
    (startup/shutdown) events. Without this, every DB-backed endpoint 500s with
    "no such table" / "relation does not exist".
    """
    from app.db.session import engine
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> Generator:
    """
    Reset auth rate limiters before each test so the per-IP windows from one
    test don't bleed into the next (every test hits the API from the same host).
    """
    from app.api.v1.auth import login_rate_limit, register_rate_limit

    login_rate_limit.limiter.reset()
    register_rate_limit.limiter.reset()
    yield


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for testing API endpoints.

    Usage:
        async def test_health(client: AsyncClient):
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def register_and_login(client: AsyncClient) -> dict:
    """
    Register a fresh user and log in.

    Returns a dict with: email, password, user_id, access_token, refresh_token,
    and ready-to-use auth `headers`.
    """
    email = f"user_{uuid.uuid4().hex[:10]}@example.com"
    password = "password123"

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Test User"},
    )
    assert reg.status_code == 201, reg.text
    user_id = reg.json()["id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    tokens = login.json()

    return {
        "email": email,
        "password": password,
        "user_id": user_id,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
    }


@pytest_asyncio.fixture
async def auth(client: AsyncClient) -> dict:
    """A registered + logged-in user with ready-to-use auth headers."""
    return await register_and_login(client)
