"""
Analysis service — orchestrates the document analysis pipeline.

Coordinates:
1. PDF text extraction
2. Document classification (syllabus vs question paper)
3. Syllabus analysis
4. Topic frequency analysis
5. Pattern detection
"""

import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipelines.classifier import Classifier
from app.ai.pipelines.document_processor import DocumentProcessor
from app.ai.pipelines.pattern_analyzer import PatternAnalyzer
from app.ai.pipelines.syllabus_analyzer import SyllabusAnalyzer
from app.config import get_settings
from app.core.exceptions import AnalysisError, DocumentNotFoundError
from app.core.logging import get_logger
from app.models import Analysis, Document, ProcessingStatus

logger = get_logger(__name__)


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
    ) -> Analysis:
        """
        Run the full analysis pipeline on a document.

        Pipeline stages:
        1. Extract text from PDF
        2. Classify pages (syllabus vs question paper)
        3. Analyze syllabus structure
        4. Analyze question paper patterns and frequency

        Returns:
            Analysis ORM object with results.
        """
        start_time = time.perf_counter()

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
            logger.info("analysis_stage", stage="pdf_extraction", document_id=str(document_id))
            pages = self.doc_processor.extract_pages_text(document.file_path)
            analysis.num_pages_processed = len(pages)

            # 3. Classify pages
            logger.info("analysis_stage", stage="classification", num_pages=len(pages))
            classification = await self.classifier.classify_document(pages)

            syllabus_text = classification["syllabus_text"]
            question_paper_text = classification["question_paper_text"]

            # 4. Analyze syllabus
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
            logger.info("analysis_stage", stage="pattern_analysis", num_papers=len(papers))
            frequency_result = await self.pattern_analyzer.analyze_frequency(papers)

            analysis.topic_frequency = frequency_result.get("frequency", [])
            analysis.pattern_analysis = frequency_result.get("patterns", {})

            # 7. Mark complete
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
