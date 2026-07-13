"""
Analysis service — orchestrates the document analysis pipeline.

Coordinates:
1. PDF text extraction
2. Document classification (syllabus vs question paper)
3. Syllabus analysis
4. Topic frequency analysis
5. Pattern detection
6. RAG indexing (vector store for semantic retrieval)
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipelines.classifier import Classifier
from app.ai.pipelines.document_processor import DocumentProcessor
from app.ai.pipelines.pattern_analyzer import PatternAnalyzer
from app.ai.pipelines.syllabus_analyzer import SyllabusAnalyzer
from app.ai.rag import RAGStore
from app.config import get_settings
from app.core.exceptions import AnalysisError, DocumentNotFoundError
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models import Analysis, Document, ProcessingStatus
from app.services.storage import read_stored_file

logger = get_logger(__name__)

# Type alias for progress callbacks used by SSE streaming
ProgressCallback = Callable[[str, int, str], Any] | None


class AnalysisService:
    """Orchestrates the full document analysis pipeline."""

    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.classifier = Classifier()
        self.syllabus_analyzer = SyllabusAnalyzer()
        self.pattern_analyzer = PatternAnalyzer()
        self.settings = get_settings()

    async def _get_document(
        self, document_id: UUID, user_id: UUID, db: AsyncSession
    ) -> Document | None:
        """Fetch a document owned by the given user."""
        stmt = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_pending_analysis(
        self,
        document_id: UUID,
        user_id: UUID,
        db: AsyncSession,
    ) -> Analysis:
        """
        Create a PROCESSING analysis record without running the pipeline.

        Used by the background-task flow so a status poll immediately finds a
        PROCESSING record before the pipeline (which runs in a separate session)
        has produced any results.
        """
        document = await self._get_document(document_id, user_id, db)
        if not document:
            raise DocumentNotFoundError(str(document_id))

        analysis = Analysis(
            document_id=document.id,
            status=ProcessingStatus.PROCESSING,
            model_used=self.settings.DEFAULT_LLM_MODEL,
        )
        db.add(analysis)
        document.status = ProcessingStatus.PROCESSING
        await db.flush()
        return analysis

    async def run_analysis_background(
        self,
        document_id: UUID,
        user_id: UUID,
        analysis_id: UUID,
    ) -> None:
        """
        Run the pipeline for an already-created analysis in its own DB session.

        Scheduled via FastAPI BackgroundTasks after the request session has been
        committed and closed, so it must open and own its own session. On failure
        the analysis/document rows are persisted as FAILED.
        """
        async with async_session_factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            document = await session.get(Document, document_id)
            if analysis is None or document is None:
                logger.error(
                    "background_analysis_records_missing",
                    analysis_id=str(analysis_id),
                    document_id=str(document_id),
                )
                return

            try:
                await self._run_pipeline(analysis, document, session)
                await session.commit()
            except Exception as e:
                # Persist the FAILED state in a clean transaction.
                await session.rollback()
                analysis = await session.get(Analysis, analysis_id)
                document = await session.get(Document, document_id)
                if analysis is not None:
                    analysis.status = ProcessingStatus.FAILED
                    analysis.error_message = str(e)[:2000]
                if document is not None:
                    document.status = ProcessingStatus.FAILED
                    document.error_message = str(e)[:2000]
                await session.commit()
                logger.error(
                    "background_analysis_failed",
                    document_id=str(document_id),
                    error=str(e),
                )

    async def run_analysis(
        self,
        document_id: UUID,
        user_id: UUID,
        db: AsyncSession,
        progress_callback: ProgressCallback = None,
    ) -> Analysis:
        """
        Run the full analysis pipeline on a document within the caller's session.

        Used by the SSE streaming pipeline, which commits the session itself.

        Pipeline stages:
        1. Extract text from PDF
        2. Classify pages (syllabus vs question paper)
        3. Analyze syllabus structure
        4. Analyze question paper patterns and frequency
        5. Index extracted data into RAG vector store

        Returns:
            Analysis ORM object with results.
        """
        # 1. Get document
        document = await self._get_document(document_id, user_id, db)
        if not document:
            raise DocumentNotFoundError(str(document_id))

        # Create analysis record
        analysis = Analysis(
            document_id=document.id,
            status=ProcessingStatus.PROCESSING,
            model_used=self.settings.DEFAULT_LLM_MODEL,
        )
        db.add(analysis)
        await db.flush()
        document.status = ProcessingStatus.PROCESSING

        await self._run_pipeline(analysis, document, db, progress_callback)
        return analysis

    async def _run_pipeline(
        self,
        analysis: Analysis,
        document: Document,
        db: AsyncSession,
        progress_callback: ProgressCallback = None,
    ) -> Analysis:
        """
        Execute the analysis pipeline against existing analysis/document rows.

        On failure the rows are marked FAILED on the in-memory objects and an
        AnalysisError is raised; callers are responsible for persisting state.
        """
        start_time = time.perf_counter()
        document_id = document.id

        async def _emit(stage: str, progress: int, detail: str) -> None:
            if progress_callback:
                await progress_callback(stage, progress, detail)

        try:
            # 2. Extract text from PDF (fetched via the storage layer so it
            # works for both local paths and object-storage URLs)
            await _emit("pdf_extraction", 10, "Extracting text from PDF...")
            logger.info("analysis_stage", stage="pdf_extraction", document_id=str(document_id))
            file_bytes = await read_stored_file(document.file_path)
            pages = self.doc_processor.extract_pages_text(file_bytes)
            analysis.num_pages_processed = len(pages)

            # 3. Classify pages
            await _emit("classifying", 20, f"Classifying {len(pages)} pages...")
            logger.info("analysis_stage", stage="classification", num_pages=len(pages))
            classification = await self.classifier.classify_document(pages)

            syllabus_text = classification["syllabus_text"]
            question_paper_text = classification["question_paper_text"]

            # 4. Analyze syllabus
            await _emit("syllabus_analysis", 35, "Extracting syllabus structure...")
            logger.info("analysis_stage", stage="syllabus_analysis")
            syllabus_structure = await self.syllabus_analyzer.analyze(syllabus_text)
            analysis.syllabus_structure = syllabus_structure.model_dump()

            # 5. Split question papers by session
            papers = self.doc_processor.split_papers_by_session(question_paper_text)
            analysis.num_papers_found = len(papers)

            # Store raw papers
            analysis.question_papers = [
                {"session": p["session"], "text": p["text"][:5000]}  # Truncate for DB
                for p in papers
            ]

            # 6. Analyze patterns and frequency
            await _emit("pattern_analysis", 50, f"Analyzing {len(papers)} question papers...")
            logger.info("analysis_stage", stage="pattern_analysis", num_papers=len(papers))
            frequency_result = await self.pattern_analyzer.analyze_frequency(papers)

            analysis.topic_frequency = frequency_result.get("frequency", [])
            analysis.pattern_analysis = frequency_result.get("patterns", {})

            # 7. Index into RAG vector store for semantic retrieval
            await _emit("rag_indexing", 65, "Indexing questions into vector store...")
            questions_indexed = await self._index_into_rag(
                db=db,
                user_id=document.user_id,
                document_id=document_id,
                frequency_result=frequency_result,
                syllabus_structure=syllabus_structure,
            )
            logger.info(
                "rag_indexing_complete",
                document_id=str(document_id),
                questions_indexed=questions_indexed,
            )

            # 8. Mark complete
            processing_time = round(time.perf_counter() - start_time, 2)
            analysis.processing_time_seconds = processing_time
            analysis.status = ProcessingStatus.COMPLETED
            analysis.completed_at = datetime.now(UTC)

            document.status = ProcessingStatus.COMPLETED

            logger.info(
                "analysis_complete",
                analysis_id=str(analysis.id),
                document_id=str(document_id),
                processing_time_seconds=processing_time,
                num_pages=len(pages),
                num_papers=len(papers),
                num_topics=len(frequency_result.get("frequency", [])),
                questions_indexed=questions_indexed,
            )

            return analysis

        except Exception as e:
            analysis.status = ProcessingStatus.FAILED
            analysis.error_message = str(e)
            document.status = ProcessingStatus.FAILED
            document.error_message = str(e)

            logger.error(
                "analysis_failed",
                analysis_id=str(analysis.id),
                document_id=str(document_id),
                error=str(e),
            )

            raise AnalysisError(f"Analysis pipeline failed: {str(e)}")

    async def _index_into_rag(
        self,
        db: AsyncSession,
        user_id: UUID,
        document_id: UUID,
        frequency_result: dict[str, Any],
        syllabus_structure: Any,
    ) -> int:
        """
        Index extracted questions and syllabus topics into the RAG vector store.

        RAG is optional: an embedding failure disables retrieval for this
        document but must never fail the analysis. The writes run inside a
        savepoint so a database error here rolls back only the chunk inserts,
        leaving the surrounding analysis transaction usable.
        """
        try:
            rag = RAGStore()
            total_indexed = 0

            async with db.begin_nested():
                # Index questions from each paper
                questions_by_paper = frequency_result.get("questions_by_paper", [])
                topic_by_session = frequency_result.get("topic_by_session", {})
                sessions = sorted(topic_by_session.keys()) if topic_by_session else []

                for i, paper_questions in enumerate(questions_by_paper):
                    session = sessions[i] if i < len(sessions) else f"paper_{i}"
                    indexed = await rag.index_questions(
                        db=db,
                        user_id=user_id,
                        document_id=document_id,
                        questions=paper_questions,
                        session=session,
                    )
                    total_indexed += indexed

                # Index syllabus topics
                if syllabus_structure and syllabus_structure.units:
                    for unit in syllabus_structure.units:
                        await rag.index_topics(
                            db=db,
                            user_id=user_id,
                            document_id=document_id,
                            topics=unit.topics,
                            unit=f"unit_{unit.unit_number}",
                        )

            return total_indexed

        except Exception as e:
            logger.warning("rag_indexing_failed", error=str(e))
            return 0

    async def get_analysis(
        self,
        document_id: UUID,
        user_id: UUID,
        db: AsyncSession,
    ) -> Analysis | None:
        """
        Get the latest analysis for a document.

        Also reaps analyses that have been PROCESSING past the timeout. On
        serverless, `BackgroundTasks` are killed when the invocation ends, so
        a run can silently die and leave the row PROCESSING forever — the UI
        would poll it indefinitely. Surfacing it as FAILED lets the user retry.
        This is a stopgap until a durable job queue lands (ROADMAP 1.3).
        """
        stmt = (
            select(Analysis)
            .join(Document)
            .where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        analysis = result.scalar_one_or_none()

        if analysis is not None and self._is_stale(analysis):
            await self._mark_stale_failed(analysis, db)

        return analysis

    def _is_stale(self, analysis: Analysis) -> bool:
        """True if this analysis has been PROCESSING beyond the timeout."""
        if analysis.status != ProcessingStatus.PROCESSING:
            return False
        if analysis.created_at is None:
            return False

        age = datetime.now(UTC) - analysis.created_at
        return age > timedelta(seconds=self.settings.ANALYSIS_TIMEOUT_SECONDS)

    async def _mark_stale_failed(self, analysis: Analysis, db: AsyncSession) -> None:
        """Persist a stuck analysis (and its document) as FAILED."""
        message = (
            "Analysis timed out — the job did not complete. This can happen if "
            "the server restarted mid-run. Please try again."
        )
        analysis.status = ProcessingStatus.FAILED
        analysis.error_message = message

        document = await db.get(Document, analysis.document_id)
        if document is not None and document.status == ProcessingStatus.PROCESSING:
            document.status = ProcessingStatus.FAILED
            document.error_message = message

        await db.flush()
        logger.warning(
            "analysis_marked_stale",
            analysis_id=str(analysis.id),
            document_id=str(analysis.document_id),
        )
