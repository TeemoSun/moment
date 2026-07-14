"""评论与点赞 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CommentAuthorOut(BaseModel):
    id: int
    nickname: str
    avatar_url: str
    is_deactivated: bool


class ReplyToOut(BaseModel):
    id: int
    nickname: str
    is_deactivated: bool


class CommentOut(BaseModel):
    id: int
    post_id: int
    author: CommentAuthorOut
    parent_comment_id: int | None
    reply_to: ReplyToOut | None
    content: str | None
    image_thumb_url: str | None
    image_large_url: str | None
    like_count: int
    liked_by_me: bool
    is_owner: bool
    can_delete: bool
    created_at: datetime


class CommentListOut(BaseModel):
    items: list[CommentOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class CommentCreateIn(BaseModel):
    content: str | None = Field(default=None, max_length=2000)
    media_id: int | None = None
    parent_comment_id: int | None = None
    reply_to_user_id: int | None = None


class LikeCountOut(BaseModel):
    target_type: str
    target_id: int
    like_count: int
    liked_by_me: bool


class CommentMediaOut(BaseModel):
    media_id: int
    image_thumb_url: str | None
    image_large_url: str | None
    status: str
