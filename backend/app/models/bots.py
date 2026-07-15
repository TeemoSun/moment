"""机器人配置表。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Bot(TimestampMixin, Base):
    __tablename__ = "bots"
    __table_args__ = (
        CheckConstraint("poll_interval_n > 0", name="ck_bots_poll_n"),
        CheckConstraint("poll_interval_x >= 0", name="ck_bots_poll_x"),
        CheckConstraint("lookback_days > 0", name="ck_bots_lookback"),
        CheckConstraint("comments_per_hour > 0", name="ck_bots_cph"),
        Index("ix_bots_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    persona: Mapped[str] = mapped_column(Text, nullable=False)
    poll_interval_n: Mapped[int] = mapped_column(
        Integer, nullable=False, default=600, server_default="600"
    )
    poll_interval_x: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60, server_default="60"
    )
    lookback_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )
    comments_per_hour: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10, server_default="10"
    )
    max_consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    auto_paused: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
