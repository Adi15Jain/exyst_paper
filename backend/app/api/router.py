"""
API router — aggregates all v1 route modules.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.health import router as health_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(analysis_router)
api_router.include_router(predictions_router)
api_router.include_router(analytics_router)
api_router.include_router(health_router)
