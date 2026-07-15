"""管理后台相关 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StatsOut(BaseModel):
    user_count: int
    post_count: int
    comment_count: int
    like_count: int
    invite_count: int
    used_invite_count: int


class AdminUserOut(BaseModel):
    id: int
    email: str
    nickname: str
    role: str
    status: str
    can_invite: bool
    avatar_url: str
    created_at: datetime
    last_login_at: datetime | None


class AdminUserListOut(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class AdminUserUpdateIn(BaseModel):
    status: Literal["active", "disabled"] | None = None
    can_invite: bool | None = None
    restore: bool | None = None


class AdminAuthorOut(BaseModel):
    id: int
    email: str
    nickname: str
    avatar_url: str
    is_deactivated: bool


class AdminPostOut(BaseModel):
    id: int
    content: str
    visibility: str
    deleted: bool
    author: AdminAuthorOut
    like_count: int
    comment_count: int
    created_at: datetime
    deleted_at: datetime | None


class AdminPostListOut(BaseModel):
    items: list[AdminPostOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class AdminCommentOut(BaseModel):
    id: int
    post_id: int
    content: str | None
    image_thumb_url: str | None
    deleted: bool
    author: AdminAuthorOut
    like_count: int
    created_at: datetime
    deleted_at: datetime | None


class AdminCommentListOut(BaseModel):
    items: list[AdminCommentOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class AdminInviteOut(BaseModel):
    id: int
    code: str
    status: str
    expires_at: datetime | None
    created_at: datetime
    used_by_id: int | None
    creator: AdminAuthorOut


class AdminInviteListOut(BaseModel):
    items: list[AdminInviteOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class LLMConfigOut(BaseModel):
    base_url: str
    model: str
    timeout: int
    max_tokens: int
    has_api_key: bool


class LLMConfigUpdateIn(BaseModel):
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=100)
    timeout: int | None = Field(default=None, ge=1, le=600)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)


class LLMConfigTestIn(BaseModel):
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=100)
    timeout: int | None = Field(default=None, ge=1, le=600)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)


class LLMTestOut(BaseModel):
    success: bool
    message: str
