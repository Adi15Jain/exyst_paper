"""
Prediction pipeline — generates predicted question papers.

Multi-step process:
1. Assemble context from syllabus + frequency data + RAG-retrieved questions
2. Construct a detailed prompt
3. Generate structured prediction via LLM (Pass 1)
4. Validate and fix the output via LLM (Pass 2)
5. Return validated prediction
"""

from datetime import datetime
from typing import Any

from app.ai.llm_client import LLMClient
from app.ai.pipelines.syllabus_analyzer import SyllabusStructure
from app.core.logging import get_logger
from app.schemas.prediction import PredictedPaper, PredictedSection

logger = get_logger(__name__)

PREDICTOR_SYSTEM_PROMPT = """You are an expert exam paper predictor for university examinations.
Based on historical question papers, syllabus structure, and topic frequency patterns,
you generate realistic predicted question papers.

CRITICAL RULES:
1. Return ONLY valid JSON matching the exact schema specified.
2. Every question must be a complete, well-formed academic question.
3. Cover topics proportionally based on their historical frequency.
4. Maintain the exam format (sections, marks distribution) from historical papers.
5. Include confidence scores (0-1) for each prediction.
6. Never generate placeholder text like "Q" or empty questions."""

PREDICTOR_USER_PROMPT = """Generate a predicted question paper based on the following data.

## Syllabus Structure
Course: {course_title}
Topics by unit:
{topics_by_unit}

## Historical Topic Frequency (most common first)
{frequency_summary}

## Topic Trends
- Rising topics (appearing more recently): {rising_topics}
- Falling topics (appearing less recently): {falling_topics}
- Consistent topics (always appear): {consistent_topics}

## Typical Question Format Pattern
{typical_question_format}

## Historical Paper Format
- Number of papers analyzed: {num_papers}
- Typical number of questions: {typical_num_questions}
- Max marks: {max_marks}
- Duration: {duration}

## RAG-Retrieved Similar Historical Questions
{rag_context}

---

## Instructions
1. The sections, question types (short/medium/long), counts, and marks distribution of the predicted paper MUST closely follow the "Typical Question Format Pattern" and typical question format from historical papers.
2. The sum of total marks for all questions in the sections MUST equal {max_marks} exactly. For example, if max_marks is 60, make sure all questions' marks sum to 60.
3. Use the RAG-retrieved similar questions as inspiration — the predicted questions should follow similar patterns, phrasing styles, and topic scopes, but NOT be exact duplicates.
4. Prioritize rising and consistent topics. De-emphasize falling topics.

Generate a complete predicted question paper as a JSON object with this EXACT structure:
{{
    "paper_info": {{
        "title": "Predicted Question Paper",
        "subject": "{course_title}",
        "academic_year": "{next_year}",
        "duration": "{duration}",
        "max_marks": "{max_marks}",
        "date": "Predicted",
        "instructions": ["Answer all questions", "..."]
    }},
    "sections": [
        {{
            "section_name": "Section A",
            "title": "Short Answer Questions",
            "description": "Answer any N questions",
            "questions": [
                {{
                    "question_number": 1,
                    "question_text": "Full question text here",
                    "topic": "Topic name",
                    "marks": 5,
                    "question_type": "short",
                    "has_parts": false,
                    "parts": [],
                    "confidence": 0.8,
                    "reasoning": "This topic appeared in 3 out of 4 papers"
                }}
            ],
            "total_marks": 20
        }}
    ],
    "total_questions": 10,
    "topic_coverage": {{"Topic A": 0.9, "Topic B": 0.7}},
    "overall_confidence": 0.75
}}
"""

VALIDATOR_SYSTEM_PROMPT = """You are a strict academic exam paper validator.
You review predicted question papers for correctness and fix any issues.
Return ONLY valid JSON matching the exact same schema as the input. No explanations."""

VALIDATOR_USER_PROMPT = """Review this predicted question paper and fix any issues:

## Validation Rules
1. Total marks across ALL questions MUST sum to exactly {max_marks}. Currently sums to {current_total}.
2. All sections must have the correct number of questions per the historical pattern.
3. No duplicate questions allowed — each must be unique.
4. Every question must be a complete, well-formed academic question (minimum 15 characters).
5. Questions should cover diverse syllabus topics — redistribute if too concentrated on one topic.
6. Confidence scores must be between 0.0 and 1.0.
7. The "total_questions" field must equal the actual count of questions across all sections.

## Current Paper (fix any violations)
{paper_json}

Return the CORRECTED paper as JSON with the exact same schema. Only fix issues — preserve everything that is already correct."""


class Predictor:
    """
    Generates predicted question papers using LLM with structured context.
    Uses a two-pass approach: Generate → Validate & Fix.

    Generation uses the default (best) model.
    Validation uses a lite model to save quota.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()
        # Use lite tier for validation — it's a simpler task
        self.llm_lite = LLMClient(tier="lite")

    async def predict(
        self,
        syllabus: SyllabusStructure,
        frequency_data: dict[str, Any],
        metadata: dict[str, str | None],
        rag_context: list[dict[str, Any]] | None = None,
    ) -> PredictedPaper:
        """
        Generate a predicted question paper.

        Args:
            syllabus: Structured syllabus data.
            frequency_data: Topic frequency and pattern analysis.
            metadata: Exam metadata (marks, duration, etc.)
            rag_context: RAG-retrieved similar historical questions.

        Returns:
            PredictedPaper with validated structure and confidence scores.
        """
        # Build context strings
        topics_by_unit = self._format_topics_by_unit(syllabus)
        frequency_summary = self._format_frequency(frequency_data)
        patterns = frequency_data.get("patterns", {})

        # Determine next academic year
        current_year = datetime.now().year
        next_year = f"{current_year}-{str(current_year + 1)[2:]}"

        # Format RAG context
        rag_context_text = self._format_rag_context(rag_context or [])

        course_title = syllabus.course_title or metadata.get("subject", "Unknown Subject")
        rising = ", ".join(patterns.get("rising_topics", [])) or "None detected"
        falling = ", ".join(patterns.get("falling_topics", [])) or "None detected"
        consistent = ", ".join(patterns.get("consistent_topics", [])) or "None detected"
        num_papers = patterns.get("total_papers_analyzed", 0)

        total_q = patterns.get("total_questions_found", 10)
        total_p = max(patterns.get("total_papers_analyzed", 1), 1)
        typical_q = total_q // total_p

        max_marks = metadata.get("max_marks", "100")

        prompt = PREDICTOR_USER_PROMPT.format(
            course_title=course_title,
            topics_by_unit=topics_by_unit,
            frequency_summary=frequency_summary,
            rising_topics=rising,
            falling_topics=falling,
            consistent_topics=consistent,
            num_papers=num_papers,
            typical_num_questions=typical_q,
            max_marks=max_marks,
            duration=metadata.get("duration", "3 Hours"),
            typical_question_format=metadata.get("typical_format", "No typical format patterns detected."),
            next_year=next_year,
            rag_context=rag_context_text,
        )

        try:
            # === Pass 1: Generate ===
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=PREDICTOR_SYSTEM_PROMPT,
                temperature=0.4,
                response_format={"type": "json_object"},
            )

            paper = response.parse_as(PredictedPaper)

            logger.info(
                "prediction_pass1_complete",
                total_questions=paper.total_questions,
                num_sections=len(paper.sections),
                overall_confidence=paper.overall_confidence,
                model=response.model,
                latency_ms=response.latency_ms,
            )

            # === Pass 2: Validate & Fix ===
            paper = await self._validate_prediction(paper, max_marks)

            return paper  # type: ignore

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}: {traceback.format_exc()}"
            logger.error("prediction_failed", error=error_msg)
            # Return a minimal valid paper rather than crashing
            return self._create_fallback_paper(syllabus, metadata, error_msg)

    async def _validate_prediction(
        self,
        paper: PredictedPaper,
        target_max_marks: str,
    ) -> PredictedPaper:
        """
        Pass 2: Validate the predicted paper and fix structural issues.

        Only runs the validation LLM call if the paper has detectable errors
        (wrong marks total, too few questions, etc.) to save API quota.
        """
        # Calculate actual total marks
        actual_total = sum(
            q.marks
            for section in paper.sections
            for q in section.questions
        )
        actual_question_count = sum(
            len(section.questions)
            for section in paper.sections
        )

        try:
            target = int(target_max_marks)
        except (ValueError, TypeError):
            target = 100

        # Check if validation is needed
        needs_fix = False
        if actual_total != target:
            logger.info(
                "validation_needed_marks_mismatch",
                actual=actual_total,
                target=target,
            )
            needs_fix = True
        if actual_question_count != paper.total_questions:
            logger.info(
                "validation_needed_question_count_mismatch",
                actual=actual_question_count,
                declared=paper.total_questions,
            )
            needs_fix = True
        if actual_question_count < 3:
            logger.info("validation_needed_too_few_questions", count=actual_question_count)
            needs_fix = True

        if not needs_fix:
            logger.info("validation_skipped_paper_is_valid")
            return paper

        # Run validation pass
        try:
            import json
            paper_json = json.dumps(paper.model_dump(), indent=2, default=str)

            validator_prompt = VALIDATOR_USER_PROMPT.format(
                max_marks=target,
                current_total=actual_total,
                paper_json=paper_json,
            )

            response = await self.llm_lite.complete(
                prompt=validator_prompt,
                system_prompt=VALIDATOR_SYSTEM_PROMPT,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            validated_paper = response.parse_as(PredictedPaper)

            logger.info(
                "prediction_pass2_validation_complete",
                original_marks=actual_total,
                validated_marks=sum(
                    q.marks
                    for s in validated_paper.sections
                    for q in s.questions
                ),
                model=response.model,
                latency_ms=response.latency_ms,
            )

            return validated_paper  # type: ignore

        except Exception as e:
            logger.warning("validation_pass_failed_using_original", error=str(e))
            # If validation fails, fix total_questions count at minimum
            paper.total_questions = actual_question_count
            return paper

    def _format_topics_by_unit(self, syllabus: SyllabusStructure) -> str:
        """Format syllabus topics for prompt context."""
        if not syllabus.units:
            return "No structured syllabus available."

        lines = []
        for unit in syllabus.units:
            topics = ", ".join(unit.topics) if unit.topics else "No topics listed"
            lines.append(f"Unit {unit.unit_number} ({unit.title}): {topics}")
        return "\n".join(lines)

    def _format_frequency(self, frequency_data: dict[str, Any]) -> str:
        """Format frequency data for prompt context."""
        freq_list = frequency_data.get("frequency", [])
        if not freq_list:
            return "No frequency data available."

        lines = []
        for item in freq_list[:15]:  # Top 15 topics
            lines.append(
                f"- {item['topic']}: appeared {item['count']} times "
                f"({item['percentage']}%), trend: {item['trend']}"
            )
        return "\n".join(lines)

    def _format_rag_context(self, rag_questions: list[dict[str, Any]]) -> str:
        """Format RAG-retrieved questions for prompt context."""
        if not rag_questions:
            return "No similar historical questions retrieved."

        lines = []
        for i, q in enumerate(rag_questions[:15], 1):  # Max 15 for token limits
            text = q.get("text", "")[:250]
            topic = q.get("topic", "Unknown")
            session = q.get("session", "")
            marks = q.get("marks", "?")
            similarity = q.get("similarity_score", 0)
            lines.append(
                f"{i}. [{topic}] ({marks} marks, session: {session}, similarity: {similarity:.2f}) {text}"
            )
        return "\n".join(lines)

    def _create_fallback_paper(
        self,
        syllabus: SyllabusStructure,
        metadata: dict[str, str | None],
        error_msg: str = "Unknown error",
    ) -> PredictedPaper:
        """Create a minimal valid paper when LLM fails."""
        current_year = datetime.now().year
        return PredictedPaper(
            paper_info={
                "title": "Predicted Question Paper",
                "subject": syllabus.course_title or metadata.get("subject", "Unknown"),
                "academic_year": f"{current_year}-{str(current_year + 1)[2:]}",
                "duration": metadata.get("duration", "3 Hours"),
                "max_marks": metadata.get("max_marks", "100"),
                "date": "Predicted",
                "instructions": ["Answer all questions"],
            },
            sections=[],
            total_questions=0,
            overall_confidence=0.0,
            is_fallback=True,
            error_message=error_msg,
        )
