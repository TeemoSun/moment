"""机器人回复记录表（幂等）。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class BotReplyLog(TimestampMixin, Base):
    __tablename__ = "bot_reply_logs"
    __table_args__ = (
        UniqueConstraint(
            "bot_user_id", "post_id", "kind", "target_comment_id", name="uq_bot_reply_target"
        ),
        Index("ix_bot_reply_logs_bot", "bot_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    target_comment_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None, server_default=None
    )
    reply_comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False
    )
