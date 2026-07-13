"""add llm_cache + rate_limit_counters (cross-instance shared state)

Moves the LLM prompt cache and the rate-limit / quota counters out of process
memory and into Postgres, so multiple serverless instances share one cache and
enforce one limit instead of each keeping a private copy.

Postgres rather than Redis: no extra service or credentials, and the latency is
irrelevant next to the multi-second LLM call a cache hit avoids.

Revision ID: 0004_add_shared_state
Revises: 0003_add_vector_chunks
Create Date: 2026-07-13
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_add_shared_state"
down_revision = "0003_add_vector_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("llm_cache"):
        op.create_table(
            "llm_cache",
            sa.Column("cache_key", sa.String(length=64), nullable=False),
            sa.Column("response", sa.Text(), nullable=False),
            sa.Column("model", sa.String(length=100), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("cache_key"),
        )
        # Expired-row sweeps scan by expiry.
        op.create_index("ix_llm_cache_expires_at", "llm_cache", ["expires_at"])

    if not inspector.has_table("rate_limit_counters"):
        op.create_table(
            "rate_limit_counters",
            sa.Column("bucket", sa.String(length=64), nullable=False),
            sa.Column("client_key", sa.String(length=200), nullable=False),
            sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("hits", sa.Integer(), nullable=False),
            # Composite PK is what makes the counter upsert atomic.
            sa.PrimaryKeyConstraint("bucket", "client_key", "window_start"),
        )


def downgrade() -> None:
    op.drop_table("rate_limit_counters")
    op.drop_index("ix_llm_cache_expires_at", table_name="llm_cache")
    op.drop_table("llm_cache")
