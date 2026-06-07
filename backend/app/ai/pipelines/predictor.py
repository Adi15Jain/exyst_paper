"""
Prediction pipeline — generates predicted question papers.

Multi-step process:
1. Assemble context from syllabus + frequency data + historical questions
2. Construct a detailed prompt
3. Generate structured prediction via LLM
4. Validate and score the output
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.ai.llm_client import LLMClient
from app.ai.pipelines.syllabus_analyzer import SyllabusStructure
from app.schemas.prediction import PredictedPaper, PredictedQuestion, PredictedSection
from app.core.logging import get_logger

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

## Historical Paper Format
- Number of papers analyzed: {num_papers}
- Typical number of questions: {typical_num_questions}
- Max marks: {max_marks}
- Duration: {duration}

## Sample Questions from Past Papers
{sample_questions}

---

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


class Predictor:
    """
    Generates predicted question papers using LLM with structured context.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

    async def predict(
        self,
        syllabus: SyllabusStructure,
        frequency_data: Dict[str, Any],
        metadata: Dict[str, Optional[str]],
        sample_questions: List[Dict[str, Any]] | None = None,
    ) -> PredictedPaper:
        """
        Generate a predicted question paper.

        Args:
            syllabus: Structured syllabus data.
            frequency_data: Topic frequency and pattern analysis.
            metadata: Exam metadata (marks, duration, etc.)
            sample_questions: Representative questions from past papers.

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

        # Format sample questions
        sample_q_text = self._format_sample_questions(sample_questions or [])

        prompt = PREDICTOR_USER_PROMPT.format(
            course_title=syllabus.course_title or metadata.get("subject", "Unknown Subject"),
            topics_by_unit=topics_by_unit,
            frequency_summary=frequency_summary,
            rising_topics=", ".join(patterns.get("rising_topics", [])) or "None detected",
            falling_topics=", ".join(patterns.get("falling_topics", [])) or "None detected",
            consistent_topics=", ".join(patterns.get("consistent_topics", [])) or "None detected",
            num_papers=patterns.get("total_papers_analyzed", 0),
            typical_num_questions=patterns.get("total_questions_found", 10) // max(patterns.get("total_papers_analyzed", 1), 1),
            max_marks=metadata.get("max_marks", "100"),
            duration=metadata.get("duration", "3 Hours"),
            next_year=next_year,
            sample_questions=sample_q_text,
        )

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=PREDICTOR_SYSTEM_PROMPT,
                temperature=0.4,
            )

            paper = response.parse_as(PredictedPaper)

            logger.info(
                "prediction_generated",
                total_questions=paper.total_questions,
                num_sections=len(paper.sections),
                overall_confidence=paper.overall_confidence,
                model=response.model,
                latency_ms=response.latency_ms,
            )

            return paper  # type: ignore

        except Exception as e:
            logger.error("prediction_failed", error=str(e))
            # Return a minimal valid paper rather than crashing
            return self._create_fallback_paper(syllabus, metadata)

    def _format_topics_by_unit(self, syllabus: SyllabusStructure) -> str:
        """Format syllabus topics for prompt context."""
        if not syllabus.units:
            return "No structured syllabus available."

        lines = []
        for unit in syllabus.units:
            topics = ", ".join(unit.topics) if unit.topics else "No topics listed"
            lines.append(f"Unit {unit.unit_number} ({unit.title}): {topics}")
        return "\n".join(lines)

    def _format_frequency(self, frequency_data: Dict[str, Any]) -> str:
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

    def _format_sample_questions(self, questions: List[Dict[str, Any]]) -> str:
        """Format sample questions for prompt context."""
        if not questions:
            return "No sample questions available."

        lines = []
        for q in questions[:10]:  # Max 10 samples
            text = q.get("question_text", q.get("text", ""))[:200]
            topic = q.get("topic", "Unknown")
            marks = q.get("marks", "?")
            lines.append(f"- [{topic}] ({marks} marks) {text}")
        return "\n".join(lines)

    def _create_fallback_paper(
        self,
        syllabus: SyllabusStructure,
        metadata: Dict[str, Optional[str]],
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
            sections=[
                PredictedSection(
                    section_name="Section A",
                    title="Questions",
                    description="Prediction generation encountered an error. Please retry.",
                    questions=[],
                    total_marks=0,
                )
            ],
            total_questions=0,
            overall_confidence=0.0,
        )
