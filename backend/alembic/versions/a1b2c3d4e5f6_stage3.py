"""stage3

Revision ID: a1b2c3d4e5f6
Revises: 5aeabc3c17c9
Create Date: 2026-07-14 01:41:23.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "5aeabc3c17c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("post_media", schema=None) as batch_op:
        batch_op.alter_column("post_id", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("thumb_path", existing_type=sa.String(500), nullable=True)
        batch_op.alter_column("large_path", existing_type=sa.String(500), nullable=True)
        batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_post_media_owner_id", "users", ["owner_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_index("ix_post_media_owner_id", ["owner_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("post_media", schema=None) as batch_op:
        batch_op.drop_index("ix_post_media_owner_id")
        batch_op.drop_constraint("fk_post_media_owner_id", type_="foreignkey")
        batch_op.drop_column("owner_id")
        batch_op.alter_column("large_path", existing_type=sa.String(500), nullable=False)
        batch_op.alter_column("thumb_path", existing_type=sa.String(500), nullable=False)
        batch_op.alter_column("post_id", existing_type=sa.Integer(), nullable=False)
