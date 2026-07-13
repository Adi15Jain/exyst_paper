"""
Cross-instance shared state, backed by Postgres.

Two things need to be shared between Vercel instances rather than living in
process memory:

  * **rate-limit / quota counters** — per-IP auth limits and per-model Gemini
    RPM tracking. In-memory counters mean every instance enforces its own
    limit and double-spends the provider quota.
  * **the LLM prompt cache** — a cache hit skips a 5–90 second Gemini call, so
    a hit on *any* instance should serve all of them.

Postgres (rather than Redis) because the app already has it, it needs no extra
service or credentials, and the latency is irrelevant here: a ~20 ms query that
avoids a multi-second LLM call is free in relative terms.

Everything in this module **fails open**. If the database hiccups, requests are
allowed through and the cache simply misses — shared state is an optimization
and a safety net, never a reason to take the API down.
"""

import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models import LLMCacheEntry, RateLimitCounter

logger = get_logger(__name__)


def _window_start(window_seconds: float) -> datetime:
    """
    Start of the current fixed window.

    Fixed windows (not sliding) so a counter is a single upsertable row. The
    tradeoff is that a burst can straddle a boundary and briefly see up to 2x
    the limit — acceptable for brute-force friction and quota pacing.
    """
    now = time.time()
    return datetime.fromtimestamp((now // window_seconds) * window_seconds, UTC)


async def increment_counter(bucket: str, key: str, window_seconds: float) -> int:
    """
    Atomically record a hit and return the count within the current window.

    Returns 0 on failure (fail open — the caller must not block the request).
    """
    window_start = _window_start(window_seconds)

    try:
        async with async_session_factory() as session:
            stmt = (
                insert(RateLimitCounter)
                .values(
                    bucket=bucket,
                    client_key=key,
                    window_start=window_start,
                    hits=1,
                )
                .on_conflict_do_update(
                    index_elements=["bucket", "client_key", "window_start"],
                    # `hits + 1` on the *existing* row — a single atomic
                    # statement, so concurrent instances can't lose an update.
                    set_={"hits": RateLimitCounter.hits + 1},
                )
                .returning(RateLimitCounter.hits)
            )
            result = await session.execute(stmt)
            hits = int(result.scalar_one())

            # A fresh window is a cheap moment to sweep stale rows.
            if hits == 1:
                await session.execute(
                    delete(RateLimitCounter).where(
                        RateLimitCounter.window_start
                        < window_start - timedelta(seconds=window_seconds * 2)
                    )
                )

            await session.commit()
            return hits

    except Exception as e:
        logger.warning("counter_increment_failed", bucket=bucket, error=str(e))
        return 0


async def counter_value(bucket: str, key: str, window_seconds: float) -> int:
    """Read a counter without incrementing it. Returns 0 on failure."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(RateLimitCounter.hits).where(
                    RateLimitCounter.bucket == bucket,
                    RateLimitCounter.client_key == key,
                    RateLimitCounter.window_start == _window_start(window_seconds),
                )
            )
            return int(result.scalar_one_or_none() or 0)

    except Exception as e:
        logger.warning("counter_read_failed", bucket=bucket, error=str(e))
        return 0


async def cache_get(cache_key: str) -> str | None:
    """Fetch a cached LLM response, or None if absent/expired/unavailable."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(LLMCacheEntry.response).where(
                    LLMCacheEntry.cache_key == cache_key,
                    LLMCacheEntry.expires_at > datetime.now(UTC),
                )
            )
            return result.scalar_one_or_none()

    except Exception as e:
        logger.warning("cache_read_failed", error=str(e))
        return None


async def cache_set(
    cache_key: str,
    response: str,
    ttl_seconds: float,
    model: str | None = None,
) -> None:
    """Store an LLM response. Silently gives up on failure."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)

    try:
        async with async_session_factory() as session:
            stmt = (
                insert(LLMCacheEntry)
                .values(
                    cache_key=cache_key,
                    response=response,
                    model=model,
                    expires_at=expires_at,
                )
                .on_conflict_do_update(
                    index_elements=["cache_key"],
                    set_={"response": response, "model": model, "expires_at": expires_at},
                )
            )
            await session.execute(stmt)

            # Expired entries are dead weight; drop them opportunistically.
            await session.execute(
                delete(LLMCacheEntry).where(LLMCacheEntry.expires_at < now)
            )
            await session.commit()

    except Exception as e:
        logger.warning("cache_write_failed", error=str(e))
