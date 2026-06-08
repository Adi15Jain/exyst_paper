"""
Prediction service — generates and stores question paper predictions.

Orchestrates:
1. Loading analysis results
2. Running the prediction pipeline
3. Evaluating prediction quality
4. Persisting results
"""

import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.evaluation import Evaluator
from app.ai.pipelines.predictor import Predictor
from app.ai.pipelines.syllabus_analyzer import SyllabusStructure
from app.config import get_settings
from app.core.exceptions import AnalysisError, PredictionError
from app.core.logging import get_logger
from app.models import Analysis, Document, Prediction, ProcessingStatus

logger = get_logger(__name__)


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
    ) -> Prediction:
        """
        Generate a prediction for a document that has been analyzed.

        Requires a completed analysis to exist.

        Returns:
            Prediction ORM object with results and confidence scores.
        """
        start_time = time.perf_counter()

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
            if analysis.pattern_analysis:
                max_marks = str(analysis.pattern_analysis.get("max_marks", "100"))
                duration = str(analysis.pattern_analysis.get("duration", "3 Hours"))
                typical_format = analysis.pattern_analysis.get("typical_question_format", typical_format)

            metadata: dict[str, str | None] = {
                "subject": syllabus.course_title or "Unknown",
                "max_marks": max_marks,
                "duration": duration,
                "typical_format": typical_format,
            }

            # 4. Prepare frequency data
            frequency_data = {
                "frequency": analysis.topic_frequency or [],
                "patterns": analysis.pattern_analysis or {},
            }

            # 5. Get sample questions from analysis
            sample_questions = []
            if analysis.pattern_analysis:
                questions_by_paper = analysis.pattern_analysis.get("questions_by_paper", [])
                for paper_qs in questions_by_paper:
                    if isinstance(paper_qs, list):
                        sample_questions.extend(paper_qs[:5])

            # 6. Generate prediction
            logger.info(
                "generating_prediction",
                analysis_id=str(analysis.id),
                document_id=str(document_id),
            )

            predicted_paper = await self.predictor.predict(
                syllabus=syllabus,
                frequency_data=frequency_data,
                metadata=metadata,
                sample_questions=sample_questions,
            )

            # 7. Evaluate prediction quality
            confidence_report = self.evaluator.evaluate(
                paper=predicted_paper,
                syllabus=syllabus,
                frequency_data=frequency_data,
            )

            # 8. Store prediction
            generation_time = round(time.perf_counter() - start_time, 2)

            prediction = Prediction(
                analysis_id=analysis.id,
                predicted_paper=predicted_paper.model_dump(),
                confidence_scores=confidence_report.model_dump(),
                overall_confidence=confidence_report.overall_confidence,
                topic_coverage=predicted_paper.topic_coverage,
                model_used=self.settings.DEFAULT_LLM_MODEL,
                prompt_version="v2.0",
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
