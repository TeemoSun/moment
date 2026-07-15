"""系统状态（单行表）。承载系统初始化标志与全局 LLM 配置。"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class SystemStatus(TimestampMixin, Base):
    __tablename__ = "system_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    initialized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    admin_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_base_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="https://api.openai.com/v1",
        server_default="https://api.openai.com/v1",
    )
    llm_api_key: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=""
    )
    llm_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="gpt-4o-mini", server_default="gpt-4o-mini"
    )
    llm_timeout: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    llm_max_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300, server_default="300"
    )
