"""媒体相关 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MediaUploadOut(BaseModel):
    media_id: int
    kind: str
    format: str
    size: int
    status: str
    created_at: datetime


class MediaOut(BaseModel):
    id: int
    post_id: int | None
    owner_id: int | None
    kind: str
    format: str
    size: int
    thumb_url: str | None
    large_url: str | None
    original_url: str | None
    sort_order: int
    created_at: datetime
