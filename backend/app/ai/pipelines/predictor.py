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
from app.schemas.prediction import PredictedPaper

logger = get_logger(__name__)

PREDICTOR_SYSTEM_PROMPT = """You are an expert exam paper setter for university examinations.

You are given the ACTUAL past question papers for a course. Your job is to set a NEW
question paper for the SAME course that a student could realistically sit next term.

CRITICAL RULES:
1. Return ONLY valid JSON matching the exact schema specified — no markdown, no prose.
2. REPLICATE THE FORMAT of the past papers exactly: the same sections, the same question
   numbering scheme, the same number of questions, the same sub-part structure (a, b, ...),
   the same per-question and per-part marks, the same internal-choice ("Or") structure, and
   the same instructions/header style. The new paper must look like it came from the same
   examiner and the same university.
3. GENERATE NEW QUESTIONS on the SAME topics, scope, and difficulty as the past papers.
   Do NOT copy any past question verbatim — rephrase, change numbers/datasets, or pick a
   sibling concept from the same topic. Numerical problems must use different values.
4. Stay strictly within the subject. Every question must clearly belong to this course —
   never invent topics from unrelated subjects.
5. The marks of all main questions MUST sum to exactly the paper's max marks.
6. Never output placeholder text like "Q" or empty questions."""

PREDICTOR_USER_PROMPT = """Set a new predicted question paper for this course.

## Course
Subject: {course_title}
Duration: {duration}
Max marks: {max_marks}

## ACTUAL PAST QUESTION PAPERS (replicate this exact format; do not copy questions verbatim)
{sample_papers}

## Topics seen across the past papers (cover these in similar proportion)
{frequency_summary}
Syllabus topics (if available): {topics_by_unit}

## Additional historical questions for reference (style/scope only)
{rag_context}

---

## How to build the paper
1. Mirror the past papers' structure EXACTLY — same sections, same question count, same
   numbering (e.g. Q1 with parts a,b,c,...; Q2–Qn as full questions), same marks per question
   and per part, and reproduce every internal "Or" choice where the originals have one.
2. The sum of all main `marks` values MUST equal {max_marks} exactly. (An "Or" alternative is
   a choice, not extra marks — do not add it to the total.)
3. Reproduce the header instructions in the same style (e.g. "Attempt all questions").
4. Write NEW questions on the same topics and difficulty; vary wording and numbers.

Return a JSON object with EXACTLY this structure:
{{
    "paper_info": {{
        "title": "Predicted Question Paper",
        "subject": "{course_title}",
        "academic_year": "{next_year}",
        "duration": "{duration}",
        "max_marks": "{max_marks}",
        "date": "Predicted",
        "instructions": ["<reproduce the paper's instructions>"]
    }},
    "sections": [
        {{
            "section_name": "<as in the source, e.g. 'Section A' or '' if the source has none>",
            "title": "<e.g. 'Short Answer Questions' or ''>",
            "description": "<e.g. 'Answer all questions'>",
            "questions": [
                {{
                    "question_number": 1,
                    "question_text": "<lead-in text, or '' if the question is only sub-parts>",
                    "topic": "<specific topic from THIS course>",
                    "marks": 10,
                    "question_type": "short",
                    "has_parts": true,
                    "parts": [
                        {{"label": "a", "question_text": "...", "marks": 2}},
                        {{"label": "b", "question_text": "...", "marks": 2}}
                    ],
                    "or_choice": {{
                        "question_text": "<the 'Or' alternative, or omit if none>",
                        "parts": [{{"label": "a", "question_text": "...", "marks": 2}}]
                    }},
                    "confidence": 0.8,
                    "reasoning": "Mirrors Q1 of the past papers; this topic recurs."
                }}
            ],
            "total_marks": 60
        }}
    ],
    "total_questions": 6,
    "topic_coverage": {{"Topic A": 0.9, "Topic B": 0.7}},
    "overall_confidence": 0.75
}}

Notes:
- If a question has no sub-parts, set "has_parts": false, "parts": [], and put the full
  question in "question_text".
- Omit "or_choice" (or set it to null) when the source question offers no alternative.
- `marks` on each main question = the total marks for that question (sum of its parts)."""

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
        sample_papers: list[dict[str, Any]] | None = None,
    ) -> PredictedPaper:
        """
        Generate a predicted question paper.

        Args:
            syllabus: Structured syllabus data.
            frequency_data: Topic frequency and pattern analysis.
            metadata: Exam metadata (subject, marks, duration, etc.)
            rag_context: RAG-retrieved similar historical questions.
            sample_papers: The actual past papers (dicts with 'session'/'text') used as the
                authoritative format + content template.

        Returns:
            PredictedPaper with validated structure and confidence scores.
        """
        # Build context strings
        topics_by_unit = self._format_topics_by_unit(syllabus)
        frequency_summary = self._format_frequency(frequency_data)

        # Determine next academic year
        current_year = datetime.now().year
        next_year = f"{current_year}-{str(current_year + 1)[2:]}"

        # Format RAG context + the actual past papers (the primary grounding)
        rag_context_text = self._format_rag_context(rag_context or [])
        sample_papers_text = self._format_sample_papers(sample_papers or [])

        course_title = (
            metadata.get("subject")
            or syllabus.course_title
            or "Unknown Subject"
        )
        max_marks = metadata.get("max_marks", "100")

        prompt = PREDICTOR_USER_PROMPT.format(
            course_title=course_title,
            topics_by_unit=topics_by_unit,
            frequency_summary=frequency_summary,
            max_marks=max_marks,
            duration=metadata.get("duration", "3 Hours"),
            next_year=next_year,
            rag_context=rag_context_text,
            sample_papers=sample_papers_text,
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

    def _format_sample_papers(self, sample_papers: list[dict[str, Any]]) -> str:
        """
        Format the actual past papers verbatim so the LLM can replicate their format.

        These are the primary grounding for both the paper structure and the topics.
        """
        if not sample_papers:
            return "No past papers available — infer a standard format."

        # Use up to 2 papers; cap each so the prompt stays within token limits.
        lines = []
        for i, paper in enumerate(sample_papers[:2], 1):
            text = (paper.get("text") or "").strip()[:4000]
            session = paper.get("session", "")
            lines.append(f"----- PAST PAPER {i} (session: {session}) -----\n{text}")
        return "\n\n".join(lines)

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
                "subject": metadata.get("subject") or syllabus.course_title or "Unknown",
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
