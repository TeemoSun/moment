"""朋友圈动态表。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Post(TimestampMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('public', 'friends')",
            name="ck_posts_visibility",
        ),
        Index("ix_posts_user_id", "user_id"),
        Index("ix_posts_created_at", "created_at"),
        Index("ix_posts_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default="public", server_default="public"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
