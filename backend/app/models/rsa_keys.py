"""RSA 密钥对（单行表）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RSAKey(Base):
    __tablename__ = "rsa_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    private_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default="CURRENT_TIMESTAMP", nullable=False)
