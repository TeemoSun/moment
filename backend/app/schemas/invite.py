"""邀请码相关 schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InviteCreateIn(BaseModel):
    duration_days: int | None = Field(default=None, ge=1, le=36500)


class InviteOut(BaseModel):
    id: int
    code: str
    status: str
    expires_at: datetime | None
    created_at: datetime
    used_by_id: int | None


class InviteActionOut(BaseModel):
    message: str
