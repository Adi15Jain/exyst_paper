"""
Prediction service — generates and stores question paper predictions.

Orchestrates:
1. Loading analysis results
2. RAG retrieval of semantically similar historical questions
3. Running the prediction pipeline
4. Evaluating prediction quality
5. Persisting results
"""

import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.evaluation import Evaluator
from app.ai.pipelines.predictor import Predictor
from app.ai.pipelines.syllabus_analyzer import SyllabusStructure
from app.ai.rag import RAGStore
from app.config import get_settings
from app.core.exceptions import AnalysisError, PredictionError
from app.core.logging import get_logger
from app.models import Analysis, Document, Prediction, ProcessingStatus

logger = get_logger(__name__)

# Type alias for progress callbacks used by SSE streaming
ProgressCallback = Callable[[str, int, str], Any] | None


class PredictionService:
    """Generates and manages predictions."""

    def __init__(self):
        self.predictor = Predictor()
        self.evaluator = Evaluator()
        self.settings = get_settings()

    async def generate_prediction(
        self,
        document_id: UUID,
        user_id: UUID,
        db: AsyncSession,
        progress_callback: ProgressCallback = None,
    ) -> Prediction:
        """
        Generate a prediction for a document that has been analyzed.

        Requires a completed analysis to exist.

        Args:
            document_id: Document to predict for.
            user_id: Owner of the document.
            db: Database session.
            progress_callback: Optional callback(stage, progress_pct, detail) for SSE streaming.

        Returns:
            Prediction ORM object with results and confidence scores.
        """
        start_time = time.perf_counter()

        async def _emit(stage: str, progress: int, detail: str) -> None:
            if progress_callback:
                await progress_callback(stage, progress, detail)

        # 1. Get completed analysis
        stmt = (
            select(Analysis)
            .join(Document)
            .where(
                Document.id == document_id,
                Document.user_id == user_id,
                Analysis.status == ProcessingStatus.COMPLETED,
            )
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        analysis = result.scalar_one_or_none()

        if not analysis:
            raise AnalysisError(
                "No completed analysis found. Run analysis before generating predictions."
            )

        try:
            # 2. Load syllabus structure
            syllabus = SyllabusStructure.model_validate(
                analysis.syllabus_structure or {}
            )

            max_marks = "100"
            duration = "3 Hours"
            typical_format = "No typical format patterns detected."
            extracted_subject = None
            if analysis.pattern_analysis:
                max_marks = str(analysis.pattern_analysis.get("max_marks", "100"))
                duration = str(analysis.pattern_analysis.get("duration", "3 Hours"))
                typical_format = analysis.pattern_analysis.get(
                    "typical_question_format", typical_format
                )
                extracted_subject = analysis.pattern_analysis.get("subject")

            # Prefer the subject extracted from the actual papers, then the syllabus.
            subject = extracted_subject or syllabus.course_title or "Unknown"

            metadata: dict[str, str | None] = {
                "subject": subject,
                "max_marks": max_marks,
                "duration": duration,
                "typical_format": typical_format,
            }

            # The actual past papers are the predictor's primary format + content template.
            sample_papers = analysis.question_papers or []

            # 3. Prepare frequency data
            frequency_data = {
                "frequency": analysis.topic_frequency or [],
                "patterns": analysis.pattern_analysis or {},
            }

            # 4. RAG retrieval — fetch semantically similar historical questions
            await _emit("rag_retrieval", 72, "Retrieving similar historical questions...")
            rag_context = await self._retrieve_rag_context(
                db=db,
                user_id=user_id,
                frequency_data=frequency_data,
                syllabus=syllabus,
            )
            logger.info(
                "rag_retrieval_complete",
                document_id=str(document_id),
                rag_questions_retrieved=len(rag_context),
            )

            # 5. Generate prediction
            await _emit("predicting", 78, "Generating predicted paper via Gemini...")
            logger.info(
                "generating_prediction",
                analysis_id=str(analysis.id),
                document_id=str(document_id),
            )

            predicted_paper = await self.predictor.predict(
                syllabus=syllabus,
                frequency_data=frequency_data,
                metadata=metadata,
                rag_context=rag_context,
                sample_papers=sample_papers,
            )

            # 6. Evaluate prediction quality
            await _emit("evaluating", 90, "Scoring prediction confidence...")
            confidence_report = self.evaluator.evaluate(
                paper=predicted_paper,
                syllabus=syllabus,
                frequency_data=frequency_data,
            )

            # 7. Store prediction
            generation_time = round(time.perf_counter() - start_time, 2)

            prediction = Prediction(
                analysis_id=analysis.id,
                predicted_paper=predicted_paper.model_dump(),
                confidence_scores=confidence_report.model_dump(),
                overall_confidence=confidence_report.overall_confidence,
                topic_coverage=predicted_paper.topic_coverage,
                model_used=self.settings.DEFAULT_LLM_MODEL,
                prompt_version="v3.0",
                generation_time_seconds=generation_time,
            )
            db.add(prediction)
            await db.flush()

            logger.info(
                "prediction_generated",
                prediction_id=str(prediction.id),
                analysis_id=str(analysis.id),
                overall_confidence=confidence_report.overall_confidence,
                generation_time_seconds=generation_time,
                total_questions=predicted_paper.total_questions,
                rag_questions_used=len(rag_context),
            )

            return prediction

        except PredictionError:
            raise
        except Exception as e:
            logger.error(
                "prediction_generation_failed",
                analysis_id=str(analysis.id),
                error=str(e),
            )
            raise PredictionError(f"Prediction generation failed: {str(e)}")

    async def _retrieve_rag_context(
        self,
        db: AsyncSession,
        user_id: UUID,
        frequency_data: dict[str, Any],
        syllabus: SyllabusStructure,
    ) -> list[dict[str, Any]]:
        """
        Retrieve semantically similar historical questions from the vector store.

        Queries the top frequent topics and the syllabus course title to build
        a rich context of relevant past questions. Retrieval is scoped to this
        user's chunks, so another user's questions can never leak into the
        prompt. RAG is optional — any failure yields an empty context and the
        prediction proceeds ungrounded.
        """
        try:
            rag = RAGStore()

            if await rag.count(db, user_id) == 0:
                logger.info("rag_empty_skipping_retrieval")
                return []

            all_retrieved: list[dict[str, Any]] = []
            seen_texts: set[str] = set()

            # Query by top frequency topics
            freq_list = frequency_data.get("frequency", [])
            queries = [item["topic"] for item in freq_list[:7]]

            # Also query by course title for broader context
            if syllabus.course_title:
                queries.append(syllabus.course_title)

            for query in queries:
                results = await rag.retrieve_similar_questions(
                    db=db, user_id=user_id, query=query, n_results=5
                )
                for r in results:
                    text_key = r.get("text", "")[:100]
                    if text_key not in seen_texts:
                        seen_texts.add(text_key)
                        all_retrieved.append(r)

            # Sort by similarity score descending, take top 20
            all_retrieved.sort(
                key=lambda x: x.get("similarity_score", 0), reverse=True
            )
            return all_retrieved[:20]

        except Exception as e:
            logger.warning("rag_retrieval_failed", error=str(e))
            return []

    async def get_prediction(
        self,
        document_id: UUID,
        user_id: UUID,
        db: AsyncSession,
    ) -> Prediction | None:
        """Get the latest prediction for a document."""
        stmt = (
            select(Prediction)
            .join(Analysis)
            .join(Document)
            .where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
            .order_by(Prediction.generated_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
