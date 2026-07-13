"""
Tests for the Postgres-backed shared state (cache + rate-limit counters).

These exist because the previous in-memory implementation was silently wrong on
multi-instance deploys: every replica kept its own counters and its own cache.
"""

import asyncio
import uuid

import pytest

from app.core.shared_state import (
    cache_get,
    cache_set,
    counter_value,
    increment_counter,
)


@pytest.mark.asyncio
async def test_counter_increments_and_reads_back():
    key = uuid.uuid4().hex

    assert await counter_value("test", key, 60) == 0

    assert await increment_counter("test", key, 60) == 1
    assert await increment_counter("test", key, 60) == 2
    assert await counter_value("test", key, 60) == 2


@pytest.mark.asyncio
async def test_counters_are_isolated_by_bucket_and_key():
    key_a, key_b = uuid.uuid4().hex, uuid.uuid4().hex

    await increment_counter("bucket_one", key_a, 60)
    await increment_counter("bucket_one", key_a, 60)
    await increment_counter("bucket_two", key_a, 60)
    await increment_counter("bucket_one", key_b, 60)

    assert await counter_value("bucket_one", key_a, 60) == 2
    assert await counter_value("bucket_two", key_a, 60) == 1
    assert await counter_value("bucket_one", key_b, 60) == 1


@pytest.mark.asyncio
async def test_concurrent_increments_do_not_lose_updates():
    """
    The whole point of moving counters to Postgres: concurrent callers (i.e.
    separate instances) must not clobber each other's increments. A read-then-
    write implementation would lose most of these.
    """
    key = uuid.uuid4().hex

    await asyncio.gather(*(increment_counter("race", key, 60) for _ in range(20)))

    assert await counter_value("race", key, 60) == 20


@pytest.mark.asyncio
async def test_cache_roundtrip():
    key = uuid.uuid4().hex

    assert await cache_get(key) is None

    await cache_set(key, "the response", ttl_seconds=60, model="test-model")
    assert await cache_get(key) == "the response"


@pytest.mark.asyncio
async def test_cache_overwrites_existing_key():
    key = uuid.uuid4().hex

    await cache_set(key, "first", ttl_seconds=60)
    await cache_set(key, "second", ttl_seconds=60)

    assert await cache_get(key) == "second"


@pytest.mark.asyncio
async def test_expired_cache_entry_is_not_returned():
    key = uuid.uuid4().hex

    # Already expired on write.
    await cache_set(key, "stale", ttl_seconds=-1)
    assert await cache_get(key) is None
