"""用户相关 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MeOut(BaseModel):
    id: int
    email: str
    nickname: str
    signature: str | None
    avatar_url: str
    role: str
    status: str
    can_invite: bool
    created_at: datetime


class MeUpdateIn(BaseModel):
    nickname: str | None = Field(default=None, min_length=3, max_length=100)
    signature: str | None = Field(default=None, max_length=500)


class PasswordChangeIn(BaseModel):
    old_password: str
    new_password: str


class OtherUserOut(BaseModel):
    id: int
    nickname: str
    signature: str | None
    avatar_url: str
    is_deactivated: bool
    created_at: datetime
    friendship_status: str


class AvatarOut(BaseModel):
    avatar_url: str
