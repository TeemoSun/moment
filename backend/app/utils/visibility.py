"""可见性判定。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.comments import Comment
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


def can_view_comment(db: Session, viewer_id: int, comment: Comment, post: Post) -> bool:
    """评论可见性。

    评论软删→False；post 软删→False；post 公开→True；
    post 仅好友→当前用户能看到的评论 = 评论作者是当前用户好友，
    或评论作者=当前用户，或评论作者=动态作者。
    验收：C(A 好友但非 B 好友)看不到 B 评论 → 用 viewer 的好友关系判定。
    """
    if comment.deleted_at is not None:
        return False
    if post.deleted_at is not None:
        return False
    if post.visibility == "public":
        return True
    if comment.user_id == viewer_id:
        return True
    if comment.user_id == post.user_id:
        return True
    return are_friends(db, viewer_id, comment.user_id)
