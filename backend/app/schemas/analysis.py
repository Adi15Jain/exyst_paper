"""
Analysis schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
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
    processing_time_seconds: Optional[float] = None
    error_message: Optional[str] = None


class SyllabusStructure(BaseModel):
    """Extracted syllabus data."""
    course_title: Optional[str] = None
    units: List[Dict[str, Any]] = []
    total_topics: int = 0


class QuestionPaperSummary(BaseModel):
    """Summary of an extracted question paper."""
    academic_session: Optional[str] = None
    total_questions: int = 0
    max_marks: Optional[int] = None
    topics_covered: List[str] = []


class AnalysisResponse(BaseModel):
    """Full analysis results."""
    id: UUID
    document_id: UUID
    status: str

    # Extracted structures
    syllabus_structure: Optional[SyllabusStructure] = None
    question_papers: List[QuestionPaperSummary] = []
    topic_frequency: List[TopicFrequency] = []
    pattern_analysis: Optional[Dict[str, Any]] = None

    # Metadata
    num_pages_processed: Optional[int] = None
    num_papers_found: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    model_used: Optional[str] = None

    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
