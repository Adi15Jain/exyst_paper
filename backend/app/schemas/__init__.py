"""
Pydantic schemas for request/response validation.
"""

from .auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from .document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)
from .analysis import (
    AnalysisResponse,
    AnalysisStatusResponse,
    TopicFrequency,
)
from .prediction import (
    PredictionResponse,
    PredictedQuestion,
    PredictedPaper,
    ConfidenceReport,
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
