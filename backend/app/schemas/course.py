"""
Course schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CourseCreateRequest(BaseModel):
    """Create a course."""
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    university: str | None = Field(default=None, max_length=255)
    semester: str | None = Field(default=None, max_length=50)


class CourseUpdateRequest(BaseModel):
    """Update a course. Omitted fields are left unchanged."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    university: str | None = Field(default=None, max_length=255)
    semester: str | None = Field(default=None, max_length=50)


class CourseResponse(BaseModel):
    """A course, with a count of the papers filed under it."""
    id: UUID
    name: str
    code: str | None = None
    university: str | None = None
    semester: str | None = None
    document_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseListResponse(BaseModel):
    """All of a user's courses."""
    courses: list[CourseResponse]
    total: int
