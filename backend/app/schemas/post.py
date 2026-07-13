"""动态相关 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PostCreateIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    media_ids: list[int] = Field(default_factory=list, max_length=9)
    visibility: Literal["public", "friends"] = "public"


class MediaBriefOut(BaseModel):
    id: int
    kind: str
    sort_order: int
    thumb_url: str | None
    large_url: str | None
    original_url: str | None


class AuthorOut(BaseModel):
    id: int
    nickname: str
    avatar_url: str
    is_deactivated: bool


class PostOut(BaseModel):
    id: int
    content: str
    visibility: str
    author: AuthorOut
    media: list[MediaBriefOut]
    like_count: int
    comment_count: int
    liked_by_me: bool
    is_owner: bool
    created_at: datetime
    updated_at: datetime


class PostDetailOut(PostOut):
    pass


class FeedOut(BaseModel):
    items: list[PostOut]
    next_cursor: str | None
    has_more: bool


class UserPostsOut(BaseModel):
    items: list[PostOut]
    next_cursor: str | None
    has_more: bool
