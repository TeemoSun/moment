"""add llm config columns to system_status

Revision ID: 0002_llm_config
Revises: 0001_pg_init
Create Date: 2026-07-15 21:10:00.000000

将大模型配置从环境变量迁移到 system_status 表，管理员可在后台页面管理。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_llm_config"
down_revision: str | Sequence[str] | None = "0001_pg_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "system_status",
        sa.Column(
            "llm_base_url",
            sa.String(length=500),
            nullable=False,
            server_default="https://api.openai.com/v1",
        ),
    )
    op.add_column(
        "system_status",
        sa.Column("llm_api_key", sa.String(length=500), nullable=False, server_default=""),
    )
    op.add_column(
        "system_status",
        sa.Column("llm_model", sa.String(length=100), nullable=False, server_default="gpt-4o-mini"),
    )
    op.add_column(
        "system_status",
        sa.Column("llm_timeout", sa.Integer(), nullable=False, server_default="30"),
    )
    op.add_column(
        "system_status",
        sa.Column("llm_max_tokens", sa.Integer(), nullable=False, server_default="300"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("system_status", "llm_max_tokens")
    op.drop_column("system_status", "llm_timeout")
    op.drop_column("system_status", "llm_model")
    op.drop_column("system_status", "llm_api_key")
    op.drop_column("system_status", "llm_base_url")
