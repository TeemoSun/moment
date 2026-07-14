"""好友相关 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FriendRequestIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class FriendUserBrief(BaseModel):
    id: int
    nickname: str
    avatar_url: str
    is_deactivated: bool


class FriendRequestOut(BaseModel):
    id: int
    requester: FriendUserBrief
    created_at: datetime


class FriendOut(BaseModel):
    id: int
    user: FriendUserBrief
    since: datetime
    requester_id: int


class FriendRequestActionOut(BaseModel):
    message: str
