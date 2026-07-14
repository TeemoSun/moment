"""评论服务：列表、创建、删除、媒体访问。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_storage_root, settings
from app.models.comments import Comment
from app.models.file_metadata import FileMetadata
from app.models.friendships import Friendship
from app.models.likes import Like
from app.models.post_media import PostMedia
from app.models.posts import Post
from app.models.users import User
from app.schemas.comment import (
    CommentAuthorOut,
    CommentListOut,
    CommentMediaOut,
    CommentOut,
    ReplyToOut,
)
from app.schemas.common import AppError, ErrorCode
from app.services.user_service import avatar_url_for
from app.storage import filekit
from app.utils.visibility import can_view_post


def _build_comment_author(user: User) -> dict:
    is_deactivated = user.status == "deactivated"
    if is_deactivated:
        return CommentAuthorOut(
            id=user.id,
            nickname="已注销",
            avatar_url="/api/v1/avatars/default",
            is_deactivated=True,
        ).model_dump(mode="json")
    return CommentAuthorOut(
        id=user.id,
        nickname=user.nickname,
        avatar_url=avatar_url_for(user),
        is_deactivated=False,
    ).model_dump(mode="json")


def list_comments(db: Session, viewer_id: int, post_id: int, page: int, page_size: int) -> dict:
    post = db.query(Post).filter(Post.id == post_id, Post.deleted_at.is_(None)).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "Post not found", 404)
    if not can_view_post(db, viewer_id, post):
        raise AppError(ErrorCode.FORBIDDEN, "No permission to view this post", 403)

    base_q = db.query(Comment).filter(
        Comment.post_id == post_id,
        Comment.deleted_at.is_(None),
    )

    if post.visibility == "friends":
        friend_ids: set[int] = set()
        friendships = (
            db.query(Friendship)
            .filter(
                Friendship.status == "accepted",
                Friendship.user_a_id == viewer_id,
            )
            .all()
        )
        for f in friendships:
            friend_ids.add(f.user_b_id)
        friendships = (
            db.query(Friendship)
            .filter(
                Friendship.status == "accepted",
                Friendship.user_b_id == viewer_id,
            )
            .all()
        )
        for f in friendships:
            friend_ids.add(f.user_a_id)
        allowed_user_ids = {viewer_id, post.user_id} | friend_ids
        base_q = base_q.filter(Comment.user_id.in_(allowed_user_ids))

    total = base_q.count()
    offset = (page - 1) * page_size
    comments = (
        base_q.order_by(Comment.created_at.asc(), Comment.id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    if not comments:
        return CommentListOut(
            items=[],
            total=total,
            page=page,
            page_size=page_size,
            has_more=False,
        ).model_dump(mode="json")

    author_ids = list({c.user_id for c in comments})
    reply_to_ids = list({c.reply_to_user_id for c in comments if c.reply_to_user_id})
    all_user_ids = list(set(author_ids + reply_to_ids))
    users = {u.id: u for u in db.query(User).filter(User.id.in_(all_user_ids)).all()}

    comment_ids = [c.id for c in comments]
    like_counts_rows = (
        db.query(Like.target_id, func.count(Like.id))
        .filter(Like.target_type == "comment", Like.target_id.in_(comment_ids))
        .group_by(Like.target_id)
        .all()
    )
    like_counts = {row[0]: row[1] for row in like_counts_rows}

    liked_by_me_set: set[int] = set()
    liked_rows = (
        db.query(Like.target_id)
        .filter(
            Like.target_type == "comment",
            Like.target_id.in_(comment_ids),
            Like.user_id == viewer_id,
        )
        .all()
    )
    liked_by_me_set = {row[0] for row in liked_rows}

    viewer = db.query(User).filter(User.id == viewer_id).first()
    is_admin = viewer is not None and viewer.role == "admin"

    items: list[dict] = []
    for c in comments:
        author = users.get(c.user_id)
        assert author is not None
        reply_to = users.get(c.reply_to_user_id) if c.reply_to_user_id else None
        reply_to_out = None
        if reply_to:
            is_deactivated = reply_to.status == "deactivated"
            reply_to_out = ReplyToOut(
                id=reply_to.id,
                nickname="已注销" if is_deactivated else reply_to.nickname,
                is_deactivated=is_deactivated,
            ).model_dump(mode="json")

        image_thumb_url = f"/api/v1/comments/{c.id}/media/thumb" if c.image_thumb_path else None
        image_large_url = f"/api/v1/comments/{c.id}/media/large" if c.image_large_path else None

        can_delete = c.user_id == viewer_id or post.user_id == viewer_id or is_admin

        items.append(
            CommentOut(
                id=c.id,
                post_id=c.post_id,
                author=_build_comment_author(author),
                parent_comment_id=c.parent_comment_id,
                reply_to=reply_to_out,
                content=c.content,
                image_thumb_url=image_thumb_url,
                image_large_url=image_large_url,
                like_count=like_counts.get(c.id, 0),
                liked_by_me=c.id in liked_by_me_set,
                is_owner=c.user_id == viewer_id,
                can_delete=can_delete,
                created_at=c.created_at,
            ).model_dump(mode="json")
        )

    has_more = offset + page_size < total
    return CommentListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    ).model_dump(mode="json")


def create_comment(db: Session, user: User, post_id: int, data: dict) -> dict:
    post = db.query(Post).filter(Post.id == post_id, Post.deleted_at.is_(None)).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "Post not found", 404)
    if not can_view_post(db, user.id, post):
        raise AppError(ErrorCode.FORBIDDEN, "No permission to comment on this post", 403)

    content = data.get("content")
    media_id = data.get("media_id")
    parent_comment_id = data.get("parent_comment_id")
    reply_to_user_id = data.get("reply_to_user_id")

    if content is not None:
        content = content.strip() if content.strip() else None

    if not content and not media_id:
        raise AppError(ErrorCode.EMPTY_COMMENT, "Comment must have content or image", 400)

    image_path = None
    image_thumb_path = None
    image_large_path = None

    if media_id:
        media = db.query(PostMedia).filter(PostMedia.id == media_id).first()
        if not media:
            raise AppError(ErrorCode.MEDIA_NOT_OWNED, "Media not found", 403)
        if media.owner_id != user.id:
            raise AppError(ErrorCode.MEDIA_NOT_OWNED, "Media not owned by user", 403)
        if media.post_id is not None:
            raise AppError(ErrorCode.MEDIA_ALREADY_USED, "Media already used", 400)
        if media.kind != "image":
            raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "Only image supported for comments", 400)
        image_path = media.file_path
        image_thumb_path = media.thumb_path
        image_large_path = media.large_path
        db.delete(media)

    if parent_comment_id:
        parent = (
            db.query(Comment)
            .filter(
                Comment.id == parent_comment_id,
                Comment.post_id == post_id,
                Comment.deleted_at.is_(None),
            )
            .first()
        )
        if not parent:
            raise AppError(ErrorCode.COMMENT_NOT_FOUND, "Parent comment not found", 404)
        if not reply_to_user_id:
            reply_to_user_id = parent.user_id

    if reply_to_user_id:
        reply_to_user = db.query(User).filter(User.id == reply_to_user_id).first()
        if not reply_to_user:
            raise AppError(ErrorCode.NOT_FOUND, "Reply-to user not found", 404)

    comment = Comment(
        post_id=post_id,
        user_id=user.id,
        parent_comment_id=parent_comment_id,
        reply_to_user_id=reply_to_user_id,
        content=content,
        image_path=image_path,
        image_thumb_path=image_thumb_path,
        image_large_path=image_large_path,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    author = db.query(User).filter(User.id == user.id).first()
    assert author is not None

    reply_to = (
        db.query(User).filter(User.id == reply_to_user_id).first() if reply_to_user_id else None
    )
    reply_to_out = None
    if reply_to:
        is_deactivated = reply_to.status == "deactivated"
        reply_to_out = ReplyToOut(
            id=reply_to.id,
            nickname="已注销" if is_deactivated else reply_to.nickname,
            is_deactivated=is_deactivated,
        ).model_dump(mode="json")

    image_thumb_url = f"/api/v1/comments/{comment.id}/media/thumb" if image_thumb_path else None
    image_large_url = f"/api/v1/comments/{comment.id}/media/large" if image_large_path else None

    can_delete = comment.user_id == user.id or post.user_id == user.id or user.role == "admin"

    return CommentOut(
        id=comment.id,
        post_id=comment.post_id,
        author=_build_comment_author(author),
        parent_comment_id=comment.parent_comment_id,
        reply_to=reply_to_out,
        content=comment.content,
        image_thumb_url=image_thumb_url,
        image_large_url=image_large_url,
        like_count=0,
        liked_by_me=False,
        is_owner=comment.user_id == user.id,
        can_delete=can_delete,
        created_at=comment.created_at,
    ).model_dump(mode="json")


def delete_comment(db: Session, user: User, comment_id: int) -> None:
    comment = (
        db.query(Comment).filter(Comment.id == comment_id, Comment.deleted_at.is_(None)).first()
    )
    if not comment:
        raise AppError(ErrorCode.COMMENT_NOT_FOUND, "Comment not found", 404)

    post = db.query(Post).filter(Post.id == comment.post_id).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "Post not found", 404)

    can_delete = comment.user_id == user.id or post.user_id == user.id or user.role == "admin"
    if not can_delete:
        raise AppError(ErrorCode.FORBIDDEN, "No permission to delete this comment", 403)

    comment.deleted_at = datetime.now(UTC)
    db.commit()


def get_comment_image(
    db: Session, viewer_id: int | None, comment_id: int, spec: str
) -> tuple[Path, str]:
    if spec not in ("thumb", "large"):
        raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid spec", 400)

    comment = (
        db.query(Comment).filter(Comment.id == comment_id, Comment.deleted_at.is_(None)).first()
    )
    if not comment:
        raise AppError(ErrorCode.COMMENT_NOT_FOUND, "Comment not found", 404)

    post = db.query(Post).filter(Post.id == comment.post_id, Post.deleted_at.is_(None)).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "Post not found", 404)
    if viewer_id is None or not can_view_post(db, viewer_id, post):
        raise AppError(ErrorCode.FORBIDDEN, "No permission to view this media", 403)

    if spec == "thumb":
        rel = comment.image_thumb_path
    else:
        rel = comment.image_large_path

    if not rel:
        raise AppError(ErrorCode.MEDIA_NOT_READY, "Media not ready yet", 404)

    abs_path = filekit.resolve_within_storage(rel)
    if not abs_path:
        raise AppError(ErrorCode.NOT_FOUND, "File not found", 404)

    return abs_path, "image/webp"


def upload_comment_image(db: Session, user: User, file: UploadFile) -> dict:
    if not file.filename:
        raise AppError(ErrorCode.VALIDATION_ERROR, "No file provided", 400)

    file.file.seek(0)
    content = file.file.read()
    max_size = settings.MEDIA_IMAGE_MAX_MB * 1024 * 1024
    if len(content) > max_size:
        raise AppError(ErrorCode.FILE_TOO_LARGE, "File too large", 413)

    kind = filekit.detect_kind(content)
    if kind != "image":
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "Only image supported for comments", 400)

    filekit.check_size(kind, len(content))
    fmt, _img = filekit.validate_image(content)
    if fmt == "jpg":
        fmt = "jpeg"
    mime = f"image/{fmt}"

    media_dir = filekit.get_media_dir()
    filename = filekit.generate_filename(fmt)
    abs_path = filekit.safe_save_bytes(media_dir, filename, content)
    storage_root = get_storage_root()
    rel_path = str(abs_path.relative_to(storage_root))

    stem = filename.rsplit(".", 1)[0]
    thumb_name = f"{stem}_thumb.webp"
    thumb_rel = str(Path(rel_path).with_name(thumb_name))
    thumb_abs = storage_root / thumb_rel

    large_name = f"{stem}_large.webp"
    large_rel = str(Path(rel_path).with_name(large_name))
    large_abs = storage_root / large_rel

    img = Image.open(abs_path)
    img.thumbnail((settings.THUMB_SIZE, settings.THUMB_SIZE))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")  # type: ignore[assignment]
    img.save(thumb_abs, format="WEBP", quality=settings.WEBP_THUMB_QUALITY)

    img2 = Image.open(abs_path)
    img2.thumbnail((settings.LARGE_SIZE, settings.LARGE_SIZE))
    if img2.mode in ("RGBA", "P"):
        img2 = img2.convert("RGB")  # type: ignore[assignment]
    img2.save(large_abs, format="WEBP", quality=settings.WEBP_LARGE_QUALITY)

    media = PostMedia(
        post_id=None,
        owner_id=user.id,
        file_path=rel_path,
        thumb_path=thumb_rel,
        large_path=large_rel,
        filename=filename,
        size=len(content),
        mime=mime,
        format=fmt,
        kind="image",
        sort_order=0,
    )
    db.add(media)
    db.flush()

    db.add(
        FileMetadata(
            storage_path=rel_path,
            original_name=file.filename or filename,
            filename=filename,
            size=len(content),
            mime=mime,
            format=fmt,
            kind="image",
            owner_id=user.id,
        )
    )
    db.add(
        FileMetadata(
            storage_path=thumb_rel,
            original_name=file.filename or filename,
            filename=thumb_name,
            size=thumb_abs.stat().st_size,
            mime="image/webp",
            format="webp",
            kind="thumb",
            owner_id=user.id,
        )
    )
    db.add(
        FileMetadata(
            storage_path=large_rel,
            original_name=file.filename or filename,
            filename=large_name,
            size=large_abs.stat().st_size,
            mime="image/webp",
            format="webp",
            kind="large",
            owner_id=user.id,
        )
    )
    db.commit()
    db.refresh(media)

    return CommentMediaOut(
        media_id=media.id,
        image_thumb_url=None,
        image_large_url=None,
        status="ready",
    ).model_dump(mode="json")
