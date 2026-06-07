"""
Exyst Backend — Application Entry Point

This is the slim entry point that wires up all components.
All business logic lives in the service and AI layers.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import register_middleware


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    # Setup structured logging
    setup_logging(debug=settings.DEBUG)

    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-Powered Exam Intelligence Platform — analyzes syllabi and past papers to predict future exam questions.",
        docs_url="/docs",
        redoc_url="/redoc",
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

    # Create upload directories
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUTS_DIR, exist_ok=True)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
