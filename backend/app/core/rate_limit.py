"""
Per-IP rate limiting, shared across instances.

Counters live in Postgres (see app/core/shared_state.py), so N serverless
replicas enforce ONE limit rather than each keeping a private in-memory window
— previously an attacker could get N× the allowance simply by being load
balanced around.

Fails open: if the database is unreachable the request is allowed through and a
warning is logged. Rate limiting is friction, not an authorization control, and
it must never be the reason the API goes down.
"""

from fastapi import Request

from app.core.exceptions import RateLimitError
from app.core.shared_state import increment_counter


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

    async def dependency(request: Request) -> None:
        # NOTE: the counter deliberately uses its own database session (inside
        # increment_counter) rather than the request's. The request session is
        # rolled back when an endpoint raises — and a *failed* login raising 401
        # is precisely the case we most need to count. Sharing the session would
        # roll the increment back and make brute-force limiting useless.
        hits = await increment_counter(bucket, _client_ip(request), window_seconds)

        # 0 means the counter failed (fail open).
        if hits and hits > max_requests:
            raise RateLimitError(retry_after=int(window_seconds))

    return dependency
