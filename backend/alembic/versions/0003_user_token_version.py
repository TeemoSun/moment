"""add users.token_version for session invalidation on password change

Revision ID: 0003_user_token_version
Revises: 0002_llm_config
Create Date: 2026-09-08 00:00:00.000000

改密后递增 token_version 使旧 JWT 失效。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_user_token_version"
down_revision: str | Sequence[str] | None = "0002_llm_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "token_version")
