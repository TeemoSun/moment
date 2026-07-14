"""点赞服务：动态与评论的点赞切换。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.comments import Comment
from app.models.likes import Like
from app.models.posts import Post
from app.models.users import User
from app.schemas.comment import LikeCountOut
from app.schemas.common import AppError, ErrorCode
from app.utils.visibility import can_view_comment, can_view_post


def toggle_post_like(db: Session, user: User, post_id: int) -> dict:
    post = db.query(Post).filter(Post.id == post_id, Post.deleted_at.is_(None)).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "Post not found", 404)
    if not can_view_post(db, user.id, post):
        raise AppError(ErrorCode.FORBIDDEN, "No permission to like this post", 403)

    _toggle(db, user, "post", post_id)

    like_count = (
        db.query(func.count(Like.id))
        .filter(Like.target_type == "post", Like.target_id == post_id)
        .scalar()
    ) or 0
    liked_by_me = (
        db.query(Like.id)
        .filter(
            Like.target_type == "post",
            Like.target_id == post_id,
            Like.user_id == user.id,
        )
        .first()
    ) is not None

    return LikeCountOut(
        target_type="post",
        target_id=post_id,
        like_count=like_count,
        liked_by_me=liked_by_me,
    ).model_dump(mode="json")


def toggle_comment_like(db: Session, user: User, comment_id: int) -> dict:
    comment = (
        db.query(Comment).filter(Comment.id == comment_id, Comment.deleted_at.is_(None)).first()
    )
    if not comment:
        raise AppError(ErrorCode.COMMENT_NOT_FOUND, "Comment not found", 404)

    post = db.query(Post).filter(Post.id == comment.post_id, Post.deleted_at.is_(None)).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "Post not found", 404)
    if not can_view_post(db, user.id, post):
        raise AppError(ErrorCode.FORBIDDEN, "No permission to like this comment", 403)
    if not can_view_comment(db, user.id, comment, post):
        raise AppError(ErrorCode.FORBIDDEN, "No permission to like this comment", 403)

    _toggle(db, user, "comment", comment_id)

    like_count = (
        db.query(func.count(Like.id))
        .filter(Like.target_type == "comment", Like.target_id == comment_id)
        .scalar()
    ) or 0
    liked_by_me = (
        db.query(Like.id)
        .filter(
            Like.target_type == "comment",
            Like.target_id == comment_id,
            Like.user_id == user.id,
        )
        .first()
    ) is not None

    return LikeCountOut(
        target_type="comment",
        target_id=comment_id,
        like_count=like_count,
        liked_by_me=liked_by_me,
    ).model_dump(mode="json")


def _toggle(db: Session, user: User, target_type: str, target_id: int) -> None:
    existing = (
        db.query(Like)
        .filter(
            Like.target_type == target_type,
            Like.target_id == target_id,
            Like.user_id == user.id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
    else:
        like = Like(
            target_type=target_type,
            target_id=target_id,
            user_id=user.id,
        )
        db.add(like)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(Like)
                .filter(
                    Like.target_type == target_type,
                    Like.target_id == target_id,
                    Like.user_id == user.id,
                )
                .first()
            )
            if existing:
                db.delete(existing)
                db.commit()
