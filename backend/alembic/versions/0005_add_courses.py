"""add courses; link documents and vector_chunks to them

Courses are the organizing unit: past papers accumulate into a per-course
corpus instead of every upload being a one-shot. RAG retrieval is then scoped
to that corpus, so a prediction is grounded on the *same subject's* history
rather than on everything the user has ever uploaded.

Both `course_id` columns are nullable — existing documents (and any deliberately
unfiled ones) keep working untouched. Deleting a course SETs NULL rather than
cascading: losing a semester of uploads because a course was deleted would be
unforgivable.

Revision ID: 0005_add_courses
Revises: 0004_add_shared_state
Create Date: 2026-07-13
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_add_courses"
down_revision = "0004_add_shared_state"
branch_labels = None
depends_on = None


def _has_column(inspector, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("courses"):
        op.create_table(
            "courses",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=True),
            sa.Column("university", sa.String(length=255), nullable=True),
            sa.Column("semester", sa.String(length=50), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_courses_user_id", "courses", ["user_id"])

    if not _has_column(inspector, "documents", "course_id"):
        op.add_column(
            "documents",
            sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_documents_course_id",
            "documents",
            "courses",
            ["course_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_documents_course_id", "documents", ["course_id"])

    if not _has_column(inspector, "vector_chunks", "course_id"):
        op.add_column(
            "vector_chunks",
            sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_vector_chunks_course_id",
            "vector_chunks",
            "courses",
            ["course_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_vector_chunks_course_id", "vector_chunks", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_vector_chunks_course_id", table_name="vector_chunks")
    op.drop_constraint("fk_vector_chunks_course_id", "vector_chunks", type_="foreignkey")
    op.drop_column("vector_chunks", "course_id")

    op.drop_index("ix_documents_course_id", table_name="documents")
    op.drop_constraint("fk_documents_course_id", "documents", type_="foreignkey")
    op.drop_column("documents", "course_id")

    op.drop_index("ix_courses_user_id", table_name="courses")
    op.drop_table("courses")
