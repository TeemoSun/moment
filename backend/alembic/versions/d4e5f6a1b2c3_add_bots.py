"""add bots

Revision ID: d4e5f6a1b2c3
Revises: c3d4e5f6a1b2
Create Date: 2026-07-15 08:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a1b2c3"
down_revision: str | Sequence[str] | None = "c3d4e5f6a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint("ck_users_role", "role IN ('admin', 'user', 'bot')")

    op.create_table(
        "bots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("persona", sa.Text(), nullable=False),
        sa.Column("poll_interval_n", sa.Integer(), nullable=False, server_default="600"),
        sa.Column("poll_interval_x", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("lookback_days", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("comments_per_hour", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_consecutive_failures", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("auto_paused", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("poll_interval_n > 0", name="ck_bots_poll_n"),
        sa.CheckConstraint("poll_interval_x >= 0", name="ck_bots_poll_x"),
        sa.CheckConstraint("lookback_days > 0", name="ck_bots_lookback"),
        sa.CheckConstraint("comments_per_hour > 0", name="ck_bots_cph"),
    )
    op.create_index("ix_bots_enabled", "bots", ["enabled"])

    op.create_table(
        "bot_reply_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "bot_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("target_comment_id", sa.Integer(), nullable=True, server_default=None),
        sa.Column(
            "reply_comment_id",
            sa.Integer(),
            sa.ForeignKey("comments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bot_user_id", "post_id", "kind", "target_comment_id", name="uq_bot_reply_target"
        ),
    )
    op.create_index("ix_bot_reply_logs_bot", "bot_reply_logs", ["bot_user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_bot_reply_logs_bot", table_name="bot_reply_logs")
    op.drop_table("bot_reply_logs")
    op.drop_index("ix_bots_enabled", table_name="bots")
    op.drop_table("bots")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint("ck_users_role", "role IN ('admin', 'user')")
