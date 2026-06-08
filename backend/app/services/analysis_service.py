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
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipelines.classifier import Classifier
from app.ai.pipelines.document_processor import DocumentProcessor
from app.ai.pipelines.pattern_analyzer import PatternAnalyzer
from app.ai.pipelines.syllabus_analyzer import SyllabusAnalyzer
from app.ai.rag import RAGPipeline
from app.config import get_settings
from app.core.exceptions import AnalysisError, DocumentNotFoundError
from app.core.logging import get_logger
from app.models import Analysis, Document, ProcessingStatus

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

    async def run_analysis(
        self,
        document_id: UUID,
        user_id: UUID,
        db: AsyncSession,
        progress_callback: ProgressCallback = None,
    ) -> Analysis:
        """
        Run the full analysis pipeline on a document.

        Pipeline stages:
        1. Extract text from PDF
        2. Classify pages (syllabus vs question paper)
        3. Analyze syllabus structure
        4. Analyze question paper patterns and frequency
        5. Index extracted data into RAG vector store

        Args:
            document_id: The document to analyze.
            user_id: Owner of the document.
            db: Database session.
            progress_callback: Optional callback(stage, progress_pct, detail) for SSE streaming.

        Returns:
            Analysis ORM object with results.
        """
        start_time = time.perf_counter()

        async def _emit(stage: str, progress: int, detail: str) -> None:
            if progress_callback:
                await progress_callback(stage, progress, detail)

        # 1. Get document
        stmt = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()

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

        # Update document status
        document.status = ProcessingStatus.PROCESSING

        try:
            # 2. Extract text from PDF
            await _emit("pdf_extraction", 10, "Extracting text from PDF...")
            logger.info("analysis_stage", stage="pdf_extraction", document_id=str(document_id))
            pages = self.doc_processor.extract_pages_text(document.file_path)
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
            questions_indexed = self._index_into_rag(
                document_id=str(document_id),
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

    def _index_into_rag(
        self,
        document_id: str,
        frequency_result: dict[str, Any],
        syllabus_structure: Any,
    ) -> int:
        """Index extracted questions and syllabus topics into the RAG vector store."""
        try:
            rag = RAGPipeline()
            total_indexed = 0

            # Index questions from each paper
            questions_by_paper = frequency_result.get("questions_by_paper", [])
            topic_by_session = frequency_result.get("topic_by_session", {})
            sessions = sorted(topic_by_session.keys()) if topic_by_session else []

            for i, paper_questions in enumerate(questions_by_paper):
                session = sessions[i] if i < len(sessions) else f"paper_{i}"
                indexed = rag.index_questions(
                    questions=paper_questions,
                    document_id=document_id,
                    session=session,
                )
                total_indexed += indexed

            # Index syllabus topics
            if syllabus_structure and syllabus_structure.units:
                for unit in syllabus_structure.units:
                    rag.index_topics(
                        topics=unit.topics,
                        document_id=document_id,
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
        """Get the latest analysis for a document."""
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
        return result.scalar_one_or_none()
