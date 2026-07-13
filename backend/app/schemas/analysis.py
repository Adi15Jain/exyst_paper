"""
Analysis schemas.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class TopicFrequency(BaseModel):
    """Topic frequency data point."""
    topic: str
    count: int
    percentage: float
    trend: str = "stable"  # rising, falling, stable


class AnalysisStatusResponse(BaseModel):
    """Lightweight status check response."""
    id: UUID
    status: str
    processing_time_seconds: float | None = None
    error_message: str | None = None


class QuestionPaperExcerpt(BaseModel):
    """
    One historical paper as stored by the analysis pipeline.

    Mirrors exactly what `AnalysisService` writes to `Analysis.question_papers`
    (`{"session", "text"}`). It previously declared a different shape
    (`academic_session`/`total_questions`/`max_marks`/`topics_covered`), none of
    which the stored dicts contain — so every paper serialized to all-defaults
    and the real session/text was silently dropped from the API response.
    """
    session: str = "Unknown"
    text: str = ""


class AnalysisResponse(BaseModel):
    """Full analysis results."""
    id: UUID
    document_id: UUID
    status: str

    # Extracted structures. `syllabus_structure` is the serialized
    # app.ai.pipelines.syllabus_analyzer.SyllabusStructure — kept as a free-form
    # dict here rather than re-declaring a second, lossy copy of that schema.
    syllabus_structure: dict[str, Any] | None = None
    question_papers: list[QuestionPaperExcerpt] = []
    topic_frequency: list[TopicFrequency] = []
    pattern_analysis: dict[str, Any] | None = None

    # Metadata
    num_pages_processed: int | None = None
    num_papers_found: int | None = None
    processing_time_seconds: float | None = None
    model_used: str | None = None

    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
