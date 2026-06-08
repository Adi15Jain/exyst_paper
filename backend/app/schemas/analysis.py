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


class SyllabusStructure(BaseModel):
    """Extracted syllabus data."""
    course_title: str | None = None
    units: list[dict[str, Any]] = []
    total_topics: int = 0


class QuestionPaperSummary(BaseModel):
    """Summary of an extracted question paper."""
    academic_session: str | None = None
    total_questions: int = 0
    max_marks: int | None = None
    topics_covered: list[str] = []


class AnalysisResponse(BaseModel):
    """Full analysis results."""
    id: UUID
    document_id: UUID
    status: str

    # Extracted structures
    syllabus_structure: SyllabusStructure | None = None
    question_papers: list[QuestionPaperSummary] = []
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
