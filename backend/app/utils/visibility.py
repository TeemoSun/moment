"""可见性判定。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.posts import Post
from app.utils.friends import are_friends


def can_view_post(db: Session, viewer_id: int | None, post: Post) -> bool:
    """当前用户能否查看该动态。public=True；friends 需好友或自己；软删 False。"""
    if post.deleted_at is not None:
        return False
    if post.visibility == "public":
        return True
    if viewer_id is None:
        return False
    if post.user_id == viewer_id:
        return True
    return are_friends(db, viewer_id, post.user_id)
