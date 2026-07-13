"""文件元数据表。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FileMetadata(Base):
    __tablename__ = "file_metadata"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('image', 'video', 'avatar', 'thumb', 'large')",
            name="ck_file_metadata_kind",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    storage_path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
