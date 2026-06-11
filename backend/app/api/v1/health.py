"""
Health check endpoint.
"""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.config import get_settings
from app.db.session import check_db_connection

router = APIRouter(tags=["Health"])

_start_time = datetime.now(UTC)


@router.get("/health")
async def health_check():
    """
    System health check.

    Returns status of all critical dependencies.
    """
    settings = get_settings()
    db_healthy = await check_db_connection()
    uptime = (datetime.now(UTC) - _start_time).total_seconds()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "version": settings.APP_VERSION,
        "environment": "development" if settings.DEBUG else "production",
        "checks": {
            "database": "connected" if db_healthy else "disconnected",
            "llm_provider": "configured" if settings.GEMINI_API_KEY else "not_configured",
        },
        "uptime_seconds": round(uptime, 1),
        "timestamp": datetime.now(UTC).isoformat(),
    }
