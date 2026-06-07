"""
FastAPI middleware for request tracking, timing, and error handling.
"""

import time
import uuid

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.exceptions import ExystBaseError
from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Adds a unique request ID to every request.
    The ID is available in response headers and in log context.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())[:8]

        # Bind request ID to structlog context for all logs in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Store on request state for use in route handlers
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Logs request duration for every API call.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catches all unhandled exceptions and returns consistent JSON error responses.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)
        except ExystBaseError as e:
            logger.warning(
                "application_error",
                error_type=type(e).__name__,
                message=e.message,
                status_code=e.status_code,
                details=e.details,
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": type(e).__name__,
                    "message": e.message,
                    "details": e.details,
                },
            )
        except Exception as e:
            logger.exception(
                "unhandled_error",
                error_type=type(e).__name__,
                message=str(e),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "InternalServerError",
                    "message": "An unexpected error occurred",
                    "details": {},
                },
            )


def register_middleware(app: FastAPI) -> None:
    """Register all middleware on the FastAPI app (order matters — last added runs first)."""
    app.add_middleware(TimingMiddleware)
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(RequestIDMiddleware)
