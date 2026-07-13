"""系统状态（单行表）。"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class SystemStatus(TimestampMixin, Base):
    __tablename__ = "system_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    initialized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    admin_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
