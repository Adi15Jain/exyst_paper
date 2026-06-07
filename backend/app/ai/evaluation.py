"""
Evaluation and confidence scoring for predictions.

Provides multi-factor confidence scoring:
- Topic coverage: how many syllabus topics are represented
- Question quality: well-formedness checks
- Historical alignment: do predictions match historical patterns
"""

from typing import Any, Dict, List

from app.ai.pipelines.syllabus_analyzer import SyllabusStructure
from app.schemas.prediction import ConfidenceReport, PredictedPaper
from app.core.logging import get_logger

logger = get_logger(__name__)


class Evaluator:
    """
    Evaluates prediction quality and computes confidence scores.
    """

    def evaluate(
        self,
        paper: PredictedPaper,
        syllabus: SyllabusStructure,
        frequency_data: Dict[str, Any],
    ) -> ConfidenceReport:
        """
        Compute a multi-factor confidence report for a predicted paper.

        Args:
            paper: The predicted paper to evaluate.
            syllabus: The syllabus structure for topic coverage.
            frequency_data: Historical frequency data for alignment.

        Returns:
            ConfidenceReport with per-factor and overall scores.
        """
        topic_coverage = self._score_topic_coverage(paper, syllabus)
        question_quality = self._score_question_quality(paper)
        historical_alignment = self._score_historical_alignment(paper, frequency_data)

        # Weighted overall confidence
        overall = (
            topic_coverage * 0.35
            + question_quality * 0.30
            + historical_alignment * 0.35
        )

        per_question = []
        for section in paper.sections:
            for q in section.questions:
                per_question.append({
                    "question_number": q.question_number,
                    "topic": q.topic,
                    "confidence": q.confidence,
                    "marks": q.marks,
                })

        report = ConfidenceReport(
            overall_confidence=round(overall, 3),
            topic_coverage_score=round(topic_coverage, 3),
            historical_alignment_score=round(historical_alignment, 3),
            question_quality_score=round(question_quality, 3),
            per_question_confidence=per_question,
        )

        logger.info(
            "evaluation_complete",
            overall_confidence=report.overall_confidence,
            topic_coverage=report.topic_coverage_score,
            question_quality=report.question_quality_score,
            historical_alignment=report.historical_alignment_score,
        )

        return report

    def _score_topic_coverage(
        self,
        paper: PredictedPaper,
        syllabus: SyllabusStructure,
    ) -> float:
        """
        Score how many syllabus topics are covered by predictions.

        Returns float 0-1.
        """
        syllabus_topics = set(t.lower() for t in syllabus.all_topics)
        if not syllabus_topics:
            return 0.5  # Can't evaluate without syllabus

        predicted_topics = set()
        for section in paper.sections:
            for q in section.questions:
                if q.topic:
                    predicted_topics.add(q.topic.lower())

        if not predicted_topics:
            return 0.0

        # Fuzzy matching: count a topic as covered if any predicted topic
        # is a substring match or vice versa
        covered = 0
        for st in syllabus_topics:
            for pt in predicted_topics:
                if st in pt or pt in st:
                    covered += 1
                    break

        return min(covered / len(syllabus_topics), 1.0)

    def _score_question_quality(self, paper: PredictedPaper) -> float:
        """
        Score the quality of generated questions.

        Checks:
        - Question text length (not too short, not empty)
        - Marks validity (positive, reasonable)
        - No placeholder text
        """
        if not paper.sections:
            return 0.0

        total_questions = 0
        quality_score_sum = 0.0

        for section in paper.sections:
            for q in section.questions:
                total_questions += 1
                score = 1.0

                # Penalize short questions
                text_len = len(q.question_text.strip())
                if text_len < 10:
                    score *= 0.1  # Nearly empty
                elif text_len < 30:
                    score *= 0.5  # Too short

                # Penalize placeholder content
                bad_markers = ["Q", "placeholder", "error", "Could not generate"]
                if any(marker in q.question_text for marker in bad_markers):
                    score *= 0.1

                # Penalize unreasonable marks
                if q.marks <= 0 or q.marks > 50:
                    score *= 0.5

                quality_score_sum += score

        if total_questions == 0:
            return 0.0

        return quality_score_sum / total_questions

    def _score_historical_alignment(
        self,
        paper: PredictedPaper,
        frequency_data: Dict[str, Any],
    ) -> float:
        """
        Score how well predictions align with historical patterns.

        Compares predicted topic distribution against historical frequency.
        """
        freq_list = frequency_data.get("frequency", [])
        if not freq_list:
            return 0.5  # Can't evaluate without data

        # Get top historical topics
        top_historical = set(
            item["topic"].lower() for item in freq_list[:10]
        )

        # Get predicted topics
        predicted_topics = set()
        for section in paper.sections:
            for q in section.questions:
                if q.topic:
                    predicted_topics.add(q.topic.lower())

        if not predicted_topics:
            return 0.0

        # Check overlap with top historical topics
        matches = 0
        for pt in predicted_topics:
            for ht in top_historical:
                if pt in ht or ht in pt:
                    matches += 1
                    break

        overlap = matches / max(len(top_historical), 1)
        return min(overlap, 1.0)
