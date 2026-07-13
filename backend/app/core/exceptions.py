"""
Custom exception hierarchy for Exyst.

All application-specific exceptions inherit from ExystBaseError,
enabling consistent error handling across the codebase.
"""

from typing import Any


class ExystBaseError(Exception):
    """Base exception for all Exyst errors."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# --- Authentication Errors ---


class AuthenticationError(ExystBaseError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, status_code=401)


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is invalid or expired."""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message=message)


class RateLimitError(ExystBaseError):
    """Raised when a client exceeds an endpoint's request rate limit."""

    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
        retry_after: int = 60,
    ):
        super().__init__(
            message=message,
            status_code=429,
            details={"retry_after": retry_after},
        )


# --- Document Errors ---


class DocumentNotFoundError(ExystBaseError):
    """Raised when a requested document doesn't exist."""

    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document not found: {document_id}",
            status_code=404,
            details={"document_id": document_id},
        )


class DocumentUploadError(ExystBaseError):
    """Raised when file upload fails validation."""

    def __init__(self, message: str = "File upload failed"):
        super().__init__(message=message, status_code=422)


class PDFParsingError(ExystBaseError):
    """Raised when PDF text extraction fails."""

    def __init__(self, message: str = "Failed to parse PDF"):
        super().__init__(message=message, status_code=422)


# --- AI / LLM Errors ---


class LLMError(ExystBaseError):
    """Raised when an LLM call fails."""

    def __init__(self, message: str = "LLM call failed", model: str = ""):
        super().__init__(
            message=message,
            status_code=502,
            details={"model": model},
        )


class LLMOutputParsingError(ExystBaseError):
    """Raised when LLM output cannot be parsed into the expected schema."""

    def __init__(self, message: str = "Failed to parse LLM output", raw_output: str = ""):
        super().__init__(
            message=message,
            status_code=502,
            details={"raw_output": raw_output[:500]},  # Truncate for safety
        )


# --- Analysis / Prediction Errors ---


class AnalysisError(ExystBaseError):
    """Raised when analysis pipeline fails."""

    def __init__(self, message: str = "Analysis failed", **kwargs):
        super().__init__(message=message, status_code=500, **kwargs)


class PredictionError(ExystBaseError):
    """Raised when prediction generation fails."""

    def __init__(self, message: str = "Prediction generation failed", **kwargs):
        super().__init__(message=message, status_code=500, **kwargs)


# --- Database Errors ---


class NotFoundError(ExystBaseError):
    """Generic not-found error."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            status_code=404,
            details={"resource": resource, "id": resource_id},
        )
