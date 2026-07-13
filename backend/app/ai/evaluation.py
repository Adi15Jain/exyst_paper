"""
Evaluation and confidence scoring for predictions.

Provides multi-factor confidence scoring:
- Topic coverage: how many syllabus topics the predicted questions touch
- Question quality: well-formedness checks
- Historical alignment: structural + topic pattern matching
- Marks distribution: alignment of marks-per-question patterns
"""

from collections import Counter
from typing import Any

from app.ai.pipelines.syllabus_analyzer import SyllabusStructure
from app.core.logging import get_logger
from app.schemas.prediction import ConfidenceReport, PredictedPaper

logger = get_logger(__name__)


class Evaluator:
    """
    Evaluates prediction quality and computes confidence scores.
    """

    def evaluate(
        self,
        paper: PredictedPaper,
        syllabus: SyllabusStructure,
        frequency_data: dict[str, Any],
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
        if getattr(paper, "is_fallback", False) or paper.total_questions == 0:
            return ConfidenceReport(
                overall_confidence=0.0,
                topic_coverage_score=0.0,
                historical_alignment_score=0.0,
                question_quality_score=0.0,
                marks_distribution_score=0.0,
                per_question_confidence=[],
            )

        topic_coverage = self._score_topic_coverage(paper, syllabus)
        question_quality = self._score_question_quality(paper)
        historical_alignment = self._score_historical_alignment(paper, frequency_data)
        marks_distribution = self._score_marks_distribution(paper)

        # Weighted overall confidence (4 factors)
        overall = (
            topic_coverage * 0.30
            + question_quality * 0.25
            + historical_alignment * 0.25
            + marks_distribution * 0.20
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
            marks_distribution_score=round(marks_distribution, 3),
            per_question_confidence=per_question,
        )

        logger.info(
            "evaluation_complete",
            overall_confidence=report.overall_confidence,
            topic_coverage=report.topic_coverage_score,
            question_quality=report.question_quality_score,
            historical_alignment=report.historical_alignment_score,
            marks_distribution=report.marks_distribution_score,
        )

        return report

    def _score_topic_coverage(
        self,
        paper: PredictedPaper,
        syllabus: SyllabusStructure,
    ) -> float:
        """
        Score how many syllabus topics are covered by predictions.

        Deterministic substring matching. (This previously attempted semantic
        matching through the vector store, but that path only ever ran locally
        — chromadb was absent in the serverless bundle — and it embedded every
        syllabus topic on each evaluation. Scoring the same way everywhere is
        worth more than the marginal recall; see ROADMAP 3c for a proper
        embedding-based coverage score.)

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
        frequency_data: dict[str, Any],
    ) -> float:
        """
        Score how well predictions align with historical patterns.

        Checks:
        1. Topic overlap with top historical topics (weighted 50%)
        2. Structural alignment: marks total, question count, section count (weighted 50%)
        """
        patterns = frequency_data.get("patterns", {})
        freq_list = frequency_data.get("frequency", [])

        # --- Part 1: Topic overlap (50% of this score) ---
        topic_overlap_score = 0.5  # Default when no data

        if freq_list:
            top_historical = set(
                item["topic"].lower() for item in freq_list[:10]
            )
            predicted_topics = set()
            for section in paper.sections:
                for q in section.questions:
                    if q.topic:
                        predicted_topics.add(q.topic.lower())

            if predicted_topics:
                matches = 0
                for pt in predicted_topics:
                    for ht in top_historical:
                        if pt in ht or ht in pt:
                            matches += 1
                            break

                topic_overlap_score = min(matches / max(len(top_historical), 1), 1.0)

        # --- Part 2: Structural alignment (50% of this score) ---
        structural_score = 0.5  # Default

        if patterns:
            scores = []

            # Marks alignment
            historical_marks = patterns.get("max_marks")
            if historical_marks:
                predicted_marks_str = paper.paper_info.get("max_marks", "100")
                try:
                    predicted_marks = int(predicted_marks_str)
                    hist_marks = int(historical_marks)
                    if predicted_marks == hist_marks:
                        scores.append(1.0)
                    elif abs(predicted_marks - hist_marks) / hist_marks <= 0.1:
                        scores.append(0.8)
                    elif abs(predicted_marks - hist_marks) / hist_marks <= 0.2:
                        scores.append(0.6)
                    else:
                        scores.append(0.3)
                except (ValueError, TypeError):
                    scores.append(0.5)

            # Question count alignment
            total_q_found = patterns.get("total_questions_found", 0)
            total_p = max(patterns.get("total_papers_analyzed", 1), 1)
            typical_q = total_q_found // total_p if total_q_found > 0 else 0

            if typical_q > 0:
                actual_q = sum(len(s.questions) for s in paper.sections)
                if actual_q == typical_q:
                    scores.append(1.0)
                elif abs(actual_q - typical_q) <= 2:
                    scores.append(0.8)
                elif abs(actual_q - typical_q) <= 5:
                    scores.append(0.6)
                else:
                    scores.append(0.3)

            if scores:
                structural_score = sum(scores) / len(scores)

        return topic_overlap_score * 0.5 + structural_score * 0.5

    def _score_marks_distribution(self, paper: PredictedPaper) -> float:
        """
        Score the internal consistency of the predicted marks distribution.

        Note: despite the name, this does NOT compare against the historical
        papers — it scores the predicted paper on its own (marks are positive
        and plausible, types and marks agree, spread isn't degenerate). It used
        to take a `frequency_data` argument that it never read. Scoring it
        against the real historical distribution is ROADMAP 3c.
        """
        # Get predicted marks distribution
        predicted_marks: list[int] = []
        predicted_types: list[str] = []
        for section in paper.sections:
            for q in section.questions:
                predicted_marks.append(q.marks)
                predicted_types.append(q.question_type)

        if not predicted_marks:
            return 0.0

        scores: list[float] = []

        # 1. Check if total marks matches target
        total_predicted = sum(predicted_marks)
        try:
            target_marks = int(paper.paper_info.get("max_marks", 100))
        except (ValueError, TypeError):
            target_marks = 100

        if total_predicted == target_marks:
            scores.append(1.0)
        elif abs(total_predicted - target_marks) <= 5:
            scores.append(0.7)
        else:
            scores.append(0.3)

        # 2. Check question type diversity
        type_counts = Counter(predicted_types)
        num_types = len(type_counts)
        if num_types >= 3:
            scores.append(1.0)
        elif num_types == 2:
            scores.append(0.7)
        else:
            scores.append(0.4)

        # 3. Check marks variety (not all same marks)
        unique_marks = len(set(predicted_marks))
        if unique_marks >= 3:
            scores.append(1.0)
        elif unique_marks == 2:
            scores.append(0.7)
        else:
            scores.append(0.4)

        return sum(scores) / len(scores) if scores else 0.5
