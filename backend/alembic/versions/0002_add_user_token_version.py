"""add users.token_version for refresh-token revocation

Refresh JWTs now carry a 'ver' claim; logout bumps this column so every
previously issued refresh token fails validation. Existing rows default to 0,
matching the version assumed for legacy tokens without the claim.

Revision ID: 0002_add_user_token_version
Revises: 0001_initial_schema
Create Date: 2026-07-13
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_user_token_version"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    # Idempotent: a database bootstrapped by Base.metadata.create_all against
    # a newer model set may already have this column.
    if _has_column("users", "token_version"):
        return

    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
