"""init (PostgreSQL)

Revision ID: 0001_pg_init
Revises:
Create Date: 2026-07-15 18:24:00.000000

一次性 PostgreSQL 初始迁移，建全量 schema（含 bots）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_pg_init"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ---- rsa_keys ----
    op.create_table(
        "rsa_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_key_pem", sa.Text(), nullable=False),
        sa.Column("private_key_pem", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---- system_status ----
    op.create_table(
        "system_status",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("initialized", sa.Boolean(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---- users ----
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("nickname", sa.String(length=100), nullable=False),
        sa.Column("signature", sa.String(length=500), nullable=True),
        sa.Column("avatar_path", sa.String(length=500), nullable=True),
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("can_invite", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("failed_login_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'user', 'bot')", name="ck_users_role"),
        sa.CheckConstraint(
            "status IN ('active', 'deactivated', 'disabled')", name="ck_users_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_status", "users", ["status"], unique=False)

    # ---- file_metadata ----
    op.create_table(
        "file_metadata",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('image', 'video', 'avatar', 'thumb', 'large')", name="ck_file_metadata_kind"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )

    # ---- friendships ----
    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_a_id", sa.Integer(), nullable=False),
        sa.Column("user_b_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'accepted')", name="ck_friendships_status"),
        sa.CheckConstraint("user_a_id < user_b_id", name="ck_friendships_user_order"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_a_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_b_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_a_id", "user_b_id", name="uq_friendships_users"),
    )

    # ---- invite_codes ----
    op.create_table(
        "invite_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("used_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'used', 'expired', 'revoked')", name="ck_invite_codes_status"
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["used_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_invite_codes_creator_id", "invite_codes", ["creator_id"], unique=False)
    op.create_index("ix_invite_codes_status", "invite_codes", ["status"], unique=False)

    # ---- likes ----
    op.create_table(
        "likes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_type IN ('post', 'comment')", name="ck_likes_target_type"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_type", "target_id", "user_id", name="uq_likes_target_user"),
    )
    op.create_index("ix_likes_target", "likes", ["target_type", "target_id"], unique=False)

    # ---- posts ----
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(length=20), server_default="public", nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("visibility IN ('public', 'friends')", name="ck_posts_visibility"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_posts_created_at", "posts", ["created_at"], unique=False)
    op.create_index("ix_posts_deleted_at", "posts", ["deleted_at"], unique=False)
    op.create_index("ix_posts_user_id", "posts", ["user_id"], unique=False)
    op.create_index("ix_posts_feed_cursor", "posts", ["created_at", "id"], unique=False)

    # ---- comments ----
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("parent_comment_id", sa.Integer(), nullable=True),
        sa.Column("reply_to_user_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("image_path", sa.String(length=500), nullable=True),
        sa.Column("image_thumb_path", sa.String(length=500), nullable=True),
        sa.Column("image_large_path", sa.String(length=500), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reply_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_created_at", "comments", ["created_at"], unique=False)
    op.create_index("ix_comments_post_id", "comments", ["post_id"], unique=False)

    # ---- post_media ----
    op.create_table(
        "post_media",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("thumb_path", sa.String(length=500), nullable=True),
        sa.Column("large_path", sa.String(length=500), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind IN ('image', 'video')", name="ck_post_media_kind"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_post_media_post_id", "post_media", ["post_id"], unique=False)
    op.create_index("ix_post_media_owner_id", "post_media", ["owner_id"], unique=False)

    # ---- bots ----
    op.create_table(
        "bots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("persona", sa.Text(), nullable=False),
        sa.Column("poll_interval_n", sa.Integer(), server_default="600", nullable=False),
        sa.Column("poll_interval_x", sa.Integer(), server_default="60", nullable=False),
        sa.Column("lookback_days", sa.Integer(), server_default="3", nullable=False),
        sa.Column("comments_per_hour", sa.Integer(), server_default="10", nullable=False),
        sa.Column("max_consecutive_failures", sa.Integer(), server_default="5", nullable=False),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("auto_paused", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("poll_interval_n > 0", name="ck_bots_poll_n"),
        sa.CheckConstraint("poll_interval_x >= 0", name="ck_bots_poll_x"),
        sa.CheckConstraint("lookback_days > 0", name="ck_bots_lookback"),
        sa.CheckConstraint("comments_per_hour > 0", name="ck_bots_cph"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_bots_user_id"),
    )
    op.create_index("ix_bots_enabled", "bots", ["enabled"], unique=False)

    # ---- bot_reply_logs ----
    op.create_table(
        "bot_reply_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bot_user_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("target_comment_id", sa.Integer(), nullable=True),
        sa.Column("reply_comment_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["bot_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reply_comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bot_user_id",
            "post_id",
            "kind",
            "target_comment_id",
            name="uq_bot_reply_target",
        ),
    )
    op.create_index("ix_bot_reply_logs_bot", "bot_reply_logs", ["bot_user_id"], unique=False)

    # ---- system_status seed row ----
    op.get_bind().execute(
        sa.text(
            "INSERT INTO system_status (id, initialized, admin_user_id, created_at, updated_at) "
            "VALUES (1, false, NULL, now(), now())"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("bot_reply_logs")
    op.drop_index("ix_bots_enabled", table_name="bots")
    op.drop_table("bots")
    op.drop_table("post_media")
    op.drop_index("ix_comments_post_id", table_name="comments")
    op.drop_index("ix_comments_created_at", table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_posts_feed_cursor", table_name="posts")
    op.drop_index("ix_posts_user_id", table_name="posts")
    op.drop_index("ix_posts_deleted_at", table_name="posts")
    op.drop_index("ix_posts_created_at", table_name="posts")
    op.drop_table("posts")
    op.drop_index("ix_likes_target", table_name="likes")
    op.drop_table("likes")
    op.drop_index("ix_invite_codes_status", table_name="invite_codes")
    op.drop_index("ix_invite_codes_creator_id", table_name="invite_codes")
    op.drop_table("invite_codes")
    op.drop_table("friendships")
    op.drop_table("file_metadata")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_table("users")
    op.drop_table("system_status")
    op.drop_table("rsa_keys")
