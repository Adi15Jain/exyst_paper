"""
Test fixtures and configuration.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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

    Requires a Postgres with pgvector available (the `vector_chunks` table uses
    the `vector` column type) — see the README for the local test-DB recipe.
    """
    from sqlalchemy import text

    from app.db.session import engine
    from app.models import Base

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator["AsyncSession", None]:
    """A database session for tests that exercise services directly."""
    from app.db.session import async_session_factory

    async with async_session_factory() as session:
        yield session
        await session.rollback()


class FakeEmbedder:
    """
    Deterministic embedder for tests — no API calls.

    Hashes tokens into a bag-of-words vector and L2-normalizes it, so texts
    sharing words land near each other under cosine distance. Good enough to
    assert that retrieval ranks related text above unrelated text; it says
    nothing about real embedding quality.
    """

    def __init__(self, dim: int | None = None) -> None:
        from app.ai.embeddings import EMBEDDING_DIM

        self.dim = dim or EMBEDDING_DIM

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import hashlib
        import math
        import re

        vectors = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in re.findall(r"[a-z0-9]+", text.lower()):
                digest = hashlib.sha256(token.encode()).digest()
                idx = int.from_bytes(digest[:4], "big") % self.dim
                vec[idx] += 1.0

            norm = math.sqrt(sum(v * v for v in vec))
            if norm == 0:
                # Zero vectors have undefined cosine distance; use a fixed unit vector.
                vec[0] = 1.0
                norm = 1.0
            vectors.append([v / norm for v in vec])

        return vectors


@pytest_asyncio.fixture(autouse=True)
async def _reset_shared_state() -> AsyncGenerator[None, None]:
    """
    Clear the shared rate-limit counters and LLM cache before each test.

    Both now live in Postgres rather than process memory, and every test hits
    the API from the same client host — so without this, one test's rate-limit
    window bleeds into the next and unrelated tests start seeing 429s.
    """
    from sqlalchemy import delete

    from app.db.session import async_session_factory
    from app.models import LLMCacheEntry, RateLimitCounter

    async with async_session_factory() as session:
        await session.execute(delete(RateLimitCounter))
        await session.execute(delete(LLMCacheEntry))
        await session.commit()
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
