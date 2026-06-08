"""
Prediction schemas — defines the structured output for LLM predictions.

These Pydantic models serve dual purpose:
1. API response validation
2. LLM structured output enforcement (reduces parse failures)
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# --- LLM Output Models (used to enforce structured LLM responses) ---


class PredictedQuestion(BaseModel):
    """A single predicted question with metadata."""
    question_number: int
    question_text: str
    topic: str = ""
    marks: int = Field(ge=1, le=100)
    question_type: Literal["short", "medium", "long"] = "medium"
    has_parts: bool = False
    parts: list[dict[str, Any]] = []
    confidence: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Model confidence in this question appearing (0-1)"
    )
    reasoning: str = Field(
        default="",
        description="Why this question is predicted to appear"
    )


class PredictedSection(BaseModel):
    """A section of the predicted paper."""
    section_name: str
    title: str
    description: str = ""
    questions: list[PredictedQuestion] = []
    total_marks: int = 0


class PredictedPaper(BaseModel):
    """Complete predicted question paper — the main LLM output schema."""
    paper_info: dict[str, Any] = Field(
        default_factory=lambda: {
            "title": "Predicted Question Paper",
            "subject": "Unknown",
            "academic_year": "",
            "duration": "3 Hours",
            "max_marks": "100",
            "instructions": ["Answer all questions"],
        }
    )
    sections: list[PredictedSection] = []
    total_questions: int = 0
    topic_coverage: dict[str, float] = Field(
        default_factory=dict,
        description="Mapping of topic → coverage percentage (0-1)"
    )
    overall_confidence: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Overall prediction confidence"
    )
    is_fallback: bool = False
    error_message: str | None = None


# --- API Response Models ---


class ConfidenceReport(BaseModel):
    """Breakdown of prediction confidence metrics."""
    overall_confidence: float
    topic_coverage_score: float = Field(
        description="What % of syllabus topics are covered"
    )
    historical_alignment_score: float = Field(
        description="How well predictions match historical patterns"
    )
    question_quality_score: float = Field(
        description="Average quality of generated questions"
    )
    marks_distribution_score: float = Field(
        default=0.0,
        description="How well marks distribution matches historical patterns"
    )
    per_question_confidence: list[dict[str, Any]] = []


class PredictionResponse(BaseModel):
    """Full prediction response for the API."""
    id: UUID
    analysis_id: UUID

    # The predicted paper
    predicted_paper: PredictedPaper

    # Quality metrics
    confidence: ConfidenceReport
    topic_coverage: dict[str, float] = {}

    # Metadata
    model_used: str | None = None
    prompt_version: str | None = None
    generation_time_seconds: float | None = None
    generated_at: datetime

    model_config = {"from_attributes": True}
