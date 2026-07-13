"""
Exyst Backend — Application Entry Point

This is the slim entry point that wires up all components.
All business logic lives in the service and AI layers.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import register_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    # --- Startup ---
    settings = get_settings()
    from app.db.session import engine
    from app.models import Base

    # In dev/test we auto-create tables for convenience. In production the schema
    # is owned by Alembic — run `alembic upgrade head` as a deploy step instead.
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

    # --- Shutdown ---
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    # Setup structured logging
    setup_logging(debug=settings.DEBUG)

    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-Powered Exam Intelligence Platform — "
            "analyzes syllabi and past papers to predict future exam questions."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom middleware (request ID, timing, error handling)
    register_middleware(app)

    # Routes
    app.include_router(api_router)

    # Local-disk upload target (unused when object storage is configured)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
