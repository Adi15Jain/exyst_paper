"""
Course endpoints — the organizing unit for a user's papers.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.schemas.course import (
    CourseCreateRequest,
    CourseListResponse,
    CourseResponse,
    CourseUpdateRequest,
)
from app.services.course_service import CourseService

router = APIRouter(prefix="/courses", tags=["Courses"])

course_service = CourseService()


@router.post("/", response_model=CourseResponse, status_code=201)
async def create_course(
    data: CourseCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a course to file papers under."""
    return await course_service.create(user_id, data, db)


@router.get("/", response_model=CourseListResponse)
async def list_courses(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's courses, with a paper count for each."""
    return await course_service.list_courses(user_id, db)


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get one course."""
    return await course_service.get_response(course_id, user_id, db)


@router.patch("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: UUID,
    data: CourseUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a course. Omitted fields are left unchanged."""
    return await course_service.update(course_id, user_id, data, db)


@router.delete("/{course_id}", status_code=204)
async def delete_course(
    course_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a course.

    Its documents are kept — they simply become unfiled. Deleting a course
    never deletes uploaded papers.
    """
    await course_service.delete(course_id, user_id, db)
