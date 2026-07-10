from __future__ import annotations

from datetime import datetime
from typing import Literal, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class RefreshOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: str
    username: str
    display_name: str
    bio: str
    avatar_url: str | None = None
    created_at: datetime


class UserBrief(ORMModel):
    id: str
    username: str
    display_name: str
    avatar_url: str | None = None


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    bio: str | None = Field(default=None, max_length=500)


class RegisterIn(BaseModel):
    invite_code: str = Field(min_length=4, max_length=64)
    username: str = Field(min_length=3, max_length=32)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class InviteCodeOut(ORMModel):
    id: str
    code: str
    max_uses: int
    used_count: int
    expires_at: datetime | None
    created_at: datetime


class PostCreate(BaseModel):
    content: str = Field(default="", max_length=2000)
    media_ids: list[str] = Field(default_factory=list)
    visibility: Literal["public", "friends"] = "public"


class PostUpdate(BaseModel):
    content: str | None = Field(default=None, max_length=2000)
    visibility: Literal["public", "friends"] | None = None


class MediaOut(ORMModel):
    id: str
    media_type: str
    mime_type: str
    file_format: str
    size_bytes: int
    width: int | None
    height: int | None
    duration: float | None
    original_filename: str
    small_url: str | None = None
    medium_url: str | None = None
    original_url: str | None = None


class PostOut(ORMModel):
    id: str
    user: UserBrief
    content: str
    visibility: str
    media: list[MediaOut] = []
    comment_count: int = 0
    like_count: int = 0
    liked: bool = False
    created_at: datetime


class PostDetailOut(PostOut):
    updated_at: datetime
    deleted_at: datetime | None = None


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    parent_id: str | None = None
    reply_to_user_id: str | None = None


class ReplyCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    reply_to_user_id: str | None = None


class CommentOut(ORMModel):
    id: str
    post_id: str
    user: UserBrief
    parent_id: str | None
    root_id: str
    reply_to_user: UserBrief | None = None
    depth: int
    content: str
    created_at: datetime
    deleted: bool = False
    reply_count: int = 0
    like_count: int = 0
    liked: bool = False


class CommentTree(ORMModel):
    root: CommentOut
    replies: list[CommentOut] = []
    total_replies: int = 0


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool


class FriendRequestOut(ORMModel):
    id: str
    requester: UserBrief
    addressee_id: str
    status: str
    created_at: datetime


class FriendOut(ORMModel):
    id: str
    user: UserBrief
    status: str
    accepted_at: datetime | None = None


class MessageOut(BaseModel):
    message: str


TokenOut.model_rebuild()
PostOut.model_rebuild()
PostDetailOut.model_rebuild()