"""add pgvector-backed vector_chunks table (replaces embedded ChromaDB)

Requires the pgvector extension. Managed Postgres (Neon, Supabase, Vercel
Postgres) ships it; `CREATE EXTENSION` below enables it.

Revision ID: 0003_add_vector_chunks
Revises: 0002_add_user_token_version
Create Date: 2026-07-13
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_add_vector_chunks"
down_revision = "0002_add_user_token_version"
branch_labels = None
depends_on = None

# Must match app.ai.embeddings.EMBEDDING_DIM (text-embedding-004).
EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Idempotent: skip if a create_all bootstrap already made the table.
    if sa.inspect(op.get_bind()).has_table("vector_chunks"):
        return

    op.create_table(
        "vector_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("chunk_key", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_key", name="uq_vector_chunks_chunk_key"),
    )
    op.create_index("ix_vector_chunks_user_id", "vector_chunks", ["user_id"])
    op.create_index("ix_vector_chunks_document_id", "vector_chunks", ["document_id"])
    op.create_index("ix_vector_chunks_kind", "vector_chunks", ["kind"])

    # HNSW index for cosine distance (the operator used by retrieval).
    op.execute(
        "CREATE INDEX ix_vector_chunks_embedding_hnsw "
        "ON vector_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_vector_chunks_embedding_hnsw", table_name="vector_chunks")
    op.drop_index("ix_vector_chunks_kind", table_name="vector_chunks")
    op.drop_index("ix_vector_chunks_document_id", table_name="vector_chunks")
    op.drop_index("ix_vector_chunks_user_id", table_name="vector_chunks")
    op.drop_table("vector_chunks")
    # The extension is left in place: other objects may depend on it.
