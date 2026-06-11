"""initial schema

Creates the baseline schema (users, documents, analyses, predictions) that was
previously produced at startup by Base.metadata.create_all. Mirrors the ORM
models in app/models exactly.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-11
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

# Shared enum type — created once below, referenced (without re-creating) by the
# status columns on `documents` and `analyses`.
processing_status = postgresql.ENUM(
    "PENDING",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    name="processingstatus",
    create_type=False,
)


def upgrade() -> None:
    processing_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", processing_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"], unique=False)

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", processing_status, nullable=False),
        sa.Column("syllabus_structure", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("question_papers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("topic_frequency", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("pattern_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("num_pages_processed", sa.Integer(), nullable=True),
        sa.Column("num_papers_found", sa.Integer(), nullable=True),
        sa.Column("processing_time_seconds", sa.Float(), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analyses_document_id", "analyses", ["document_id"], unique=False)

    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("predicted_paper", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("topic_coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("prompt_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generation_time_seconds", sa.Float(), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_analysis_id", "predictions", ["analysis_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_predictions_analysis_id", table_name="predictions")
    op.drop_table("predictions")
    op.drop_index("ix_analyses_document_id", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    processing_status.drop(op.get_bind(), checkfirst=True)
