"""
Document schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentRenameRequest(BaseModel):
    """Rename a document (display name only; the stored file is untouched)."""
    original_filename: str = Field(min_length=1, max_length=500)


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    id: UUID
    filename: str
    file_size_bytes: int
    status: str
    uploaded_at: datetime
    message: str = "Document uploaded successfully"
    # True when an identical file was already analyzed and its existing
    # document was returned instead of re-running the pipeline.
    deduplicated: bool = False

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Full document details."""
    id: UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    status: str
    error_message: str | None = None
    uploaded_at: datetime
    course_id: UUID | None = None
    has_analysis: bool = False
    has_prediction: bool = False

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    documents: list[DocumentResponse]
    total: int
    page: int = 1
    per_page: int = 20
