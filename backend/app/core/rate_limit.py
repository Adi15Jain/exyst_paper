"""
Lightweight in-process rate limiting.

A sliding-window limiter keyed by client IP + bucket name. Kept in memory so it
works on serverless/single-instance deployments (e.g. Vercel) without a Redis
dependency. This is brute-force friction for auth endpoints, not a distributed
rate limiter — across many instances each instance enforces its own window.
"""

import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.exceptions import RateLimitError


class SlidingWindowRateLimiter:
    """Tracks request timestamps per key within a rolling time window."""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        """Record a hit for ``key``; raise RateLimitError if over the limit."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        hits = self._hits[key]

        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now - hits[0])))
            raise RateLimitError(retry_after=retry_after)

        hits.append(now)

        # Opportunistic cleanup so idle keys don't accumulate forever.
        if len(self._hits) > 10_000:
            self._evict_empty()

    def _evict_empty(self) -> None:
        empty = [k for k, v in self._hits.items() if not v]
        for k in empty:
            del self._hits[k]

    def reset(self) -> None:
        """Clear all tracked state (used in tests)."""
        self._hits.clear()


def _client_ip(request: Request) -> str:
    """Best-effort client IP, honoring a single proxy hop via X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str, max_requests: int, window_seconds: float):
    """
    Build a FastAPI dependency that enforces a per-IP rate limit.

    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit("login", 5, 60))])
    """
    limiter = SlidingWindowRateLimiter(max_requests, window_seconds)

    async def dependency(request: Request) -> None:
        limiter.check(f"{bucket}:{_client_ip(request)}")

    # Expose the limiter so tests can reset it between cases.
    dependency.limiter = limiter  # type: ignore[attr-defined]
    return dependency
