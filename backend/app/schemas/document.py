"""
Document schemas.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    id: UUID
    filename: str
    file_size_bytes: int
    status: str
    uploaded_at: datetime
    message: str = "Document uploaded successfully"

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Full document details."""
    id: UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    status: str
    error_message: Optional[str] = None
    uploaded_at: datetime
    has_analysis: bool = False
    has_prediction: bool = False

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    documents: List[DocumentResponse]
    total: int
    page: int = 1
    per_page: int = 20
