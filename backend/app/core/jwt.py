"""JWT 工具：签发/解析。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import settings


def create_access_token(user_id: int, role: str) -> str:
    """payload: {sub: user_id, role, iat, exp=now+JWT_EXPIRE_DAYS}。HS256 + settings.JWT_SECRET。"""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """解析；过期抛 ExpiredSignatureError，非法抛 InvalidTokenError。返回 payload。"""
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
