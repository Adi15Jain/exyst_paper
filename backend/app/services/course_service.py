"""
Course service — the organizing unit for a user's documents.

A course groups the papers for one subject so they accumulate into a corpus.
That corpus is what RAG retrieval is scoped to at prediction time.
"""

from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models import Course, Document
from app.schemas.course import (
    CourseCreateRequest,
    CourseListResponse,
    CourseResponse,
    CourseUpdateRequest,
)

logger = get_logger(__name__)


class CourseService:
    """CRUD for courses, always scoped to the owning user."""

    async def create(
        self, user_id: UUID, data: CourseCreateRequest, db: AsyncSession
    ) -> CourseResponse:
        course = Course(
            user_id=user_id,
            name=data.name.strip(),
            code=data.code,
            university=data.university,
            semester=data.semester,
        )
        db.add(course)
        await db.flush()

        logger.info("course_created", course_id=str(course.id), user_id=str(user_id))
        return self._to_response(course, document_count=0)

    async def get(self, course_id: UUID, user_id: UUID, db: AsyncSession) -> Course:
        """
        Fetch a course owned by this user.

        Raises:
            NotFoundError: If missing or owned by someone else — the same
                response either way, so this can't be used to probe for the
                existence of other users' courses.
        """
        result = await db.execute(
            select(Course).where(Course.id == course_id, Course.user_id == user_id)
        )
        course = result.scalar_one_or_none()

        if not course:
            raise NotFoundError("Course", str(course_id))

        return course

    async def get_response(
        self, course_id: UUID, user_id: UUID, db: AsyncSession
    ) -> CourseResponse:
        """Fetch a course as its API representation, paper count included."""
        course = await self.get(course_id, user_id, db)
        return self._to_response(course, await self._document_count(course_id, db))

    async def list_courses(self, user_id: UUID, db: AsyncSession) -> CourseListResponse:
        """All of a user's courses, each with the number of papers filed under it."""
        doc_counts = (
            select(Document.course_id, func.count().label("n"))
            .where(Document.user_id == user_id, Document.course_id.isnot(None))
            .group_by(Document.course_id)
            .subquery()
        )

        result = await db.execute(
            select(Course, func.coalesce(doc_counts.c.n, 0))
            .outerjoin(doc_counts, doc_counts.c.course_id == Course.id)
            .where(Course.user_id == user_id)
            .order_by(Course.created_at.desc())
        )
        rows = result.all()

        courses = [self._to_response(course, count) for course, count in rows]
        return CourseListResponse(courses=courses, total=len(courses))

    async def update(
        self,
        course_id: UUID,
        user_id: UUID,
        data: CourseUpdateRequest,
        db: AsyncSession,
    ) -> CourseResponse:
        course = await self.get(course_id, user_id, db)

        # Only apply fields the client actually sent, so a partial update can't
        # silently blank out the others.
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(course, field, value.strip() if isinstance(value, str) else value)

        await db.flush()
        return self._to_response(course, await self._document_count(course_id, db))

    async def delete(self, course_id: UUID, user_id: UUID, db: AsyncSession) -> None:
        """
        Delete a course.

        Its documents are NOT deleted — they're unfiled (`course_id` → NULL) by
        the FK's ON DELETE SET NULL. Wiping a semester of uploads because
        someone tidied up their course list would be indefensible.
        """
        course = await self.get(course_id, user_id, db)
        await db.delete(course)
        await db.flush()

        logger.info("course_deleted", course_id=str(course_id), user_id=str(user_id))

    async def _document_count(self, course_id: UUID, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.course_id == course_id)
        )
        return result.scalar() or 0

    def _to_response(self, course: Course, document_count: int) -> CourseResponse:
        return CourseResponse(
            id=cast(Any, course.id),
            name=cast(Any, course.name),
            code=cast(Any, course.code),
            university=cast(Any, course.university),
            semester=cast(Any, course.semester),
            document_count=document_count,
            created_at=cast(Any, course.created_at),
        )
