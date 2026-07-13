"""
Document service — handles file upload, storage, and retrieval.
"""

import hashlib
import os
import time
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.exceptions import DocumentNotFoundError, DocumentUploadError
from app.core.logging import get_logger
from app.models import Analysis, Document, ProcessingStatus
from app.schemas.document import DocumentListResponse, DocumentResponse, DocumentUploadResponse
from app.services.storage import delete_stored_file, save_upload

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

        # Validate the bytes are actually a PDF, not just a .pdf extension.
        if not file_content.startswith(b"%PDF-"):
            raise DocumentUploadError("File is not a valid PDF")

        # Dedup: an identical file this user already uploaded and analyzed is
        # returned as-is rather than re-running the (LLM-expensive) pipeline.
        # Scoped to the owner on purpose — reusing another user's analysis
        # would leak their document's existence and needs a shared-corpus
        # design first (see ROADMAP 3a).
        file_hash = hashlib.sha256(file_content).hexdigest()
        existing = await self._find_analyzed_duplicate(user_id, file_hash, db)
        if existing is not None:
            logger.info(
                "document_upload_deduplicated",
                document_id=str(existing.id),
                user_id=str(user_id),
                file_hash=file_hash,
            )
            return DocumentUploadResponse(
                id=cast(Any, existing.id),
                filename=cast(Any, existing.original_filename),
                file_size_bytes=cast(Any, existing.file_size_bytes),
                status=existing.status.value,
                uploaded_at=cast(Any, existing.uploaded_at),
                message="This file was already analyzed — reusing the existing results.",
                deduplicated=True,
            )

        # Save file. Strip any directory components from the client-supplied
        # filename so embedded "../" sequences can't escape the upload dir.
        timestamp = int(time.time())
        base_name = os.path.basename(filename).replace(" ", "_")
        safe_name = base_name.lstrip(".") or "upload.pdf"
        stored_filename = f"{timestamp}_{safe_name}"

        # Local disk on long-lived hosts; Vercel Blob (URL) on serverless.
        file_path = await save_upload(f"{user_id}/{stored_filename}", file_content)

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
            id=cast(Any, document.id),
            filename=filename,
            file_size_bytes=len(file_content),
            status=document.status.value,
            uploaded_at=cast(Any, document.uploaded_at),
        )

    async def _find_analyzed_duplicate(
        self,
        user_id: UUID,
        file_hash: str,
        db: AsyncSession,
    ) -> Document | None:
        """
        Find this user's most recent copy of an identical file that already
        has a COMPLETED analysis. Documents that failed or never ran are not
        reused — the user is retrying for a reason.
        """
        stmt = (
            select(Document)
            .join(Analysis)
            .where(
                Document.user_id == user_id,
                Document.file_hash == file_hash,
                Analysis.status == ProcessingStatus.COMPLETED,
            )
            .order_by(Document.uploaded_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

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

    async def delete_document(
        self,
        document_id: UUID,
        user_id: UUID,
        db: AsyncSession,
    ) -> None:
        """
        Delete a document, its analyses/predictions, and its stored file.

        Raises:
            DocumentNotFoundError: If not found or belongs to another user.
        """
        # Load the full relationship tree so the ORM cascade can delete child
        # rows without triggering lazy loads (which fail under asyncio).
        stmt = (
            select(Document)
            .where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
            .options(
                selectinload(Document.analyses).selectinload(Analysis.predictions)
            )
        )
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            raise DocumentNotFoundError(str(document_id))

        file_path = doc.file_path
        await db.delete(doc)
        await db.flush()

        # Only after the rows are gone; best-effort (never blocks the delete).
        await delete_stored_file(file_path)

        logger.info(
            "document_deleted",
            document_id=str(document_id),
            user_id=str(user_id),
        )

    async def rename_document(
        self,
        document_id: UUID,
        user_id: UUID,
        new_name: str,
        db: AsyncSession,
    ) -> Document:
        """
        Change a document's display name (original_filename).

        Raises:
            DocumentNotFoundError: If not found or belongs to another user.
        """
        doc = await self.get_document(document_id, user_id, db)
        doc.original_filename = new_name.strip()
        await db.flush()
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
            .options(
                selectinload(Document.analyses).selectinload(Analysis.predictions)
            )
            .order_by(Document.uploaded_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await db.execute(stmt)
        documents = result.scalars().all()

        doc_responses = [
            DocumentResponse(
                id=cast(Any, doc.id),
                filename=cast(Any, doc.filename),
                original_filename=cast(Any, doc.original_filename),
                file_size_bytes=cast(Any, doc.file_size_bytes),
                status=doc.status.value,
                error_message=cast(Any, doc.error_message),
                uploaded_at=cast(Any, doc.uploaded_at),
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
