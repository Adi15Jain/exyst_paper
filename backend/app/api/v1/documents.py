"""
Document management endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models import Document
from app.schemas.document import (
    DocumentListResponse,
    DocumentRenameRequest,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])

document_service = DocumentService()

# Uploads write to disk and feed the LLM pipeline — keep bursts bounded.
upload_rate_limit = rate_limit("upload", max_requests=20, window_seconds=600)


def _document_response(doc: Document) -> DocumentResponse:
    """The wire shape of a single document, shared by fetch and rename."""
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_size_bytes=doc.file_size_bytes,
        status=doc.status.value,
        error_message=doc.error_message,
        uploaded_at=doc.uploaded_at,
        course_id=doc.course_id,
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
    dependencies=[Depends(upload_rate_limit)],
)
async def upload_document(
    file: UploadFile = File(...),
    course_id: UUID | None = Form(None),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a PDF document for analysis.

    Pass `course_id` to file the paper under a course — it then joins that
    course's retrieval corpus. Optional; documents can stay unfiled.
    """
    content = await file.read()
    return await document_service.upload(
        user_id=user_id,
        filename=file.filename or "unnamed.pdf",
        file_content=content,
        db=db,
        course_id=course_id,
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    course_id: UUID | None = Query(None, description="Only papers filed under this course"),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's documents, optionally filtered to one course."""
    return await document_service.list_documents(
        user_id=user_id,
        db=db,
        page=page,
        per_page=per_page,
        course_id=course_id,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific document."""
    doc = await document_service.get_document(document_id, user_id, db)
    return _document_response(doc)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def rename_document(
    document_id: UUID,
    data: DocumentRenameRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Rename a document (display name only)."""
    doc = await document_service.rename_document(
        document_id, user_id, data.original_filename, db
    )
    return _document_response(doc)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document, its analyses/predictions, and the stored file."""
    await document_service.delete_document(document_id, user_id, db)
