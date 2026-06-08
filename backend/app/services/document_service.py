"""
Document service — handles file upload, storage, and retrieval.
"""

import hashlib
import os
import time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import DocumentNotFoundError, DocumentUploadError
from app.core.logging import get_logger
from app.models import Document, ProcessingStatus
from app.schemas.document import DocumentListResponse, DocumentResponse, DocumentUploadResponse

logger = get_logger(__name__)


class DocumentService:
    """Handles document upload, storage, and retrieval."""

    def __init__(self):
        self.settings = get_settings()
        os.makedirs(self.settings.UPLOAD_DIR, exist_ok=True)

    async def upload(
        self,
        user_id: UUID,
        filename: str,
        file_content: bytes,
        db: AsyncSession,
    ) -> DocumentUploadResponse:
        """
        Save an uploaded file and create a database record.

        Raises:
            DocumentUploadError: If file validation fails.
        """
        # Validate
        if not filename.lower().endswith(".pdf"):
            raise DocumentUploadError("Only PDF files are accepted")

        if len(file_content) > self.settings.max_upload_size_bytes:
            raise DocumentUploadError(
                f"File exceeds maximum size of {self.settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        if len(file_content) == 0:
            raise DocumentUploadError("Empty file uploaded")

        # Save file
        timestamp = int(time.time())
        safe_name = filename.replace(" ", "_")
        stored_filename = f"{timestamp}_{safe_name}"

        # Create user-specific directory
        user_dir = os.path.join(self.settings.UPLOAD_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)

        file_path = os.path.join(user_dir, stored_filename)
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Compute file hash
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Create DB record
        document = Document(
            user_id=user_id,
            filename=stored_filename,
            original_filename=filename,
            file_path=file_path,
            file_hash=file_hash,
            file_size_bytes=len(file_content),
            status=ProcessingStatus.PENDING,
        )
        db.add(document)
        await db.flush()

        logger.info(
            "document_uploaded",
            document_id=str(document.id),
            user_id=str(user_id),
            filename=filename,
            size_bytes=len(file_content),
        )

        return DocumentUploadResponse(
            id=document.id,
            filename=filename,
            file_size_bytes=len(file_content),
            status=document.status.value,
            uploaded_at=document.uploaded_at,
        )

    async def get_document(
        self,
        document_id: UUID,
        user_id: UUID,
        db: AsyncSession,
    ) -> Document:
        """
        Get a document by ID, scoped to the user.

        Raises:
            DocumentNotFoundError: If not found or belongs to another user.
        """
        stmt = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            raise DocumentNotFoundError(str(document_id))

        return doc

    async def list_documents(
        self,
        user_id: UUID,
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
    ) -> DocumentListResponse:
        """List all documents for a user with pagination."""
        # Count total
        count_stmt = select(func.count()).select_from(Document).where(
            Document.user_id == user_id
        )
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Fetch page
        offset = (page - 1) * per_page
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.uploaded_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await db.execute(stmt)
        documents = result.scalars().all()

        doc_responses = [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                original_filename=doc.original_filename,
                file_size_bytes=doc.file_size_bytes,
                status=doc.status.value,
                error_message=doc.error_message,
                uploaded_at=doc.uploaded_at,
                has_analysis=bool(doc.analyses),
                has_prediction=any(
                    bool(a.predictions) for a in doc.analyses
                ) if doc.analyses else False,
            )
            for doc in documents
        ]

        return DocumentListResponse(
            documents=doc_responses,
            total=total,
            page=page,
            per_page=per_page,
        )
