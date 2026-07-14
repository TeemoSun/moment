"""stage7 invite expires_at nullable

Revision ID: c3d4e5f6a1b2
Revises: b2c3d4e5f6a1
Create Date: 2026-07-14 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a1b2"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("invite_codes", schema=None) as batch_op:
        batch_op.alter_column(
            "expires_at", existing_type=sa.DateTime(), nullable=True
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("invite_codes", schema=None) as batch_op:
        batch_op.alter_column(
            "expires_at", existing_type=sa.DateTime(), nullable=False
        )
