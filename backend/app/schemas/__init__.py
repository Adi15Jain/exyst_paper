"""
Pydantic schemas for request/response validation.
"""

from .analysis import (
    AnalysisResponse,
    AnalysisStatusResponse,
    TopicFrequency,
)
from .auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from .document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from .prediction import (
    ConfidenceReport,
    PredictedPaper,
    PredictedQuestion,
    PredictionResponse,
)

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    "DocumentResponse",
    "DocumentListResponse",
    "DocumentUploadResponse",
    "AnalysisResponse",
    "AnalysisStatusResponse",
    "TopicFrequency",
    "PredictionResponse",
    "PredictedQuestion",
    "PredictedPaper",
    "ConfidenceReport",
]
