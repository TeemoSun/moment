"""动态服务：创建、Feed、详情、删除、用户动态。"""

from __future__ import annotations

import base64
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.comments import Comment
from app.models.friendships import Friendship
from app.models.likes import Like
from app.models.post_media import PostMedia
from app.models.posts import Post
from app.models.users import User
from app.schemas.common import AppError, ErrorCode
from app.schemas.post import (
    AuthorOut,
    FeedOut,
    MediaBriefOut,
    PostCreateIn,
    PostOut,
    UserPostsOut,
)
from app.services.user_service import avatar_url_for
from app.utils.visibility import can_view_post


def _encode_cursor(created_at: datetime, post_id: int) -> str:
    dt = created_at.replace(microsecond=0)
    s = dt.strftime("%Y-%m-%d %H:%M:%S")
    return base64.urlsafe_b64encode(f"{s}|{post_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        decoded = base64.urlsafe_b64decode(cursor).decode()
        parts = decoded.rsplit("|", 1)
        if len(parts) != 2:
            raise ValueError
        dt = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
        return dt, int(parts[1])
    except Exception:
        raise AppError(ErrorCode.INVALID_CURSOR, "Invalid cursor", 400) from None


def _build_author(user: User) -> dict:
    is_deactivated = user.status == "deactivated"
    if is_deactivated:
        return AuthorOut(
            id=user.id,
            nickname="已注销",
            avatar_url="/api/v1/avatars/default",
            is_deactivated=True,
        ).model_dump(mode="json")
    return AuthorOut(
        id=user.id,
        nickname=user.nickname,
        avatar_url=avatar_url_for(user),
        is_deactivated=False,
    ).model_dump(mode="json")


def _media_brief(post_id: int, media: PostMedia) -> dict:
    def _url(spec: str, path: str | None) -> str | None:
        if path is None:
            return None
        return f"/api/v1/posts/{post_id}/media/{media.id}/{spec}"

    return MediaBriefOut(
        id=media.id,
        kind=media.kind,
        sort_order=media.sort_order,
        thumb_url=_url("thumb", media.thumb_path),
        large_url=_url("large", media.large_path),
        original_url=_url("original", media.file_path),
    ).model_dump(mode="json")


def post_to_out(db: Session, post: Post, viewer_id: int) -> dict:
    author = db.query(User).filter(User.id == post.user_id).first()
    assert author is not None
    media_rows = (
        db.query(PostMedia)
        .filter(PostMedia.post_id == post.id)
        .order_by(PostMedia.sort_order)
        .all()
    )
    like_count = (
        db.query(func.count(Like.id))
        .filter(Like.target_type == "post", Like.target_id == post.id)
        .scalar()
    ) or 0
    comment_count = (
        db.query(func.count(Comment.id))
        .filter(Comment.post_id == post.id, Comment.deleted_at.is_(None))
        .scalar()
    ) or 0
    liked_by_me = (
        db.query(Like.id)
        .filter(
            Like.target_type == "post",
            Like.target_id == post.id,
            Like.user_id == viewer_id,
        )
        .first()
    ) is not None

    return PostOut(
        id=post.id,
        content=post.content,
        visibility=post.visibility,
        author=_build_author(author),
        media=[_media_brief(post.id, m) for m in media_rows],
        like_count=like_count,
        comment_count=comment_count,
        liked_by_me=liked_by_me,
        is_owner=post.user_id == viewer_id,
        created_at=post.created_at,
        updated_at=post.updated_at,
    ).model_dump(mode="json")


def _posts_to_out(db: Session, posts: list[Post], viewer_id: int) -> list[dict]:
    if not posts:
        return []
    post_ids = [p.id for p in posts]
    author_ids = list({p.user_id for p in posts})

    authors = {u.id: u for u in db.query(User).filter(User.id.in_(author_ids)).all()}

    media_rows = (
        db.query(PostMedia)
        .filter(PostMedia.post_id.in_(post_ids))
        .order_by(PostMedia.post_id, PostMedia.sort_order)
        .all()
    )
    media_by_post: dict[int, list[PostMedia]] = {}
    for m in media_rows:
        assert m.post_id is not None
        media_by_post.setdefault(m.post_id, []).append(m)

    like_counts_rows = (
        db.query(Like.target_id, func.count(Like.id))
        .filter(Like.target_type == "post", Like.target_id.in_(post_ids))
        .group_by(Like.target_id)
        .all()
    )
    like_counts = {row[0]: row[1] for row in like_counts_rows}

    comment_counts_rows = (
        db.query(Comment.post_id, func.count(Comment.id))
        .filter(Comment.post_id.in_(post_ids), Comment.deleted_at.is_(None))
        .group_by(Comment.post_id)
        .all()
    )
    comment_counts = {row[0]: row[1] for row in comment_counts_rows}

    liked_by_me_set: set[int] = set()
    liked_rows = (
        db.query(Like.target_id)
        .filter(
            Like.target_type == "post",
            Like.target_id.in_(post_ids),
            Like.user_id == viewer_id,
        )
        .all()
    )
    liked_by_me_set = {row[0] for row in liked_rows}

    results: list[dict] = []
    for post in posts:
        author = authors.get(post.user_id)
        assert author is not None
        medias = media_by_post.get(post.id, [])
        results.append(
            PostOut(
                id=post.id,
                content=post.content,
                visibility=post.visibility,
                author=_build_author(author),
                media=[_media_brief(post.id, m) for m in medias],
                like_count=like_counts.get(post.id, 0),
                comment_count=comment_counts.get(post.id, 0),
                liked_by_me=post.id in liked_by_me_set,
                is_owner=post.user_id == viewer_id,
                created_at=post.created_at,
                updated_at=post.updated_at,
            ).model_dump(mode="json")
        )
    return results


def create_post(db: Session, user: User, data: PostCreateIn) -> dict:
    if data.media_ids:
        if len(set(data.media_ids)) != len(data.media_ids):
            raise AppError(ErrorCode.VALIDATION_ERROR, "Duplicate media id", 400)
        media_objs = db.query(PostMedia).filter(PostMedia.id.in_(data.media_ids)).all()
        media_by_id = {m.id: m for m in media_objs}
        for mid in data.media_ids:
            m = media_by_id.get(mid)
            if m is None:
                raise AppError(ErrorCode.MEDIA_NOT_OWNED, "Media not found", 403)
            if m.owner_id != user.id:
                raise AppError(ErrorCode.MEDIA_NOT_OWNED, "Media not owned by user", 403)
            if m.post_id is not None:
                raise AppError(ErrorCode.MEDIA_ALREADY_USED, "Media already used", 400)

    post = Post(
        user_id=user.id,
        content=data.content,
        visibility=data.visibility,
    )
    db.add(post)
    db.flush()

    if data.media_ids:
        for idx, mid in enumerate(data.media_ids):
            m = media_by_id[mid]
            m.post_id = post.id
            m.sort_order = idx

    db.commit()
    db.refresh(post)
    return post_to_out(db, post, viewer_id=user.id)


def get_feed(db: Session, viewer_id: int, cursor: str | None, limit: int = 20) -> dict:
    friend_ids: list[int] = []
    friendships = (
        db.query(Friendship)
        .filter(
            Friendship.status == "accepted",
            or_(
                Friendship.user_a_id == viewer_id,
                Friendship.user_b_id == viewer_id,
            ),
        )
        .all()
    )
    for f in friendships:
        friend_ids.append(f.user_b_id if f.user_a_id == viewer_id else f.user_a_id)

    base_q = db.query(Post).filter(Post.deleted_at.is_(None))

    if friend_ids:
        visibility_cond = or_(
            Post.visibility == "public",
            Post.user_id == viewer_id,
            and_(Post.visibility == "friends", Post.user_id.in_(friend_ids)),
        )
    else:
        visibility_cond = or_(
            Post.visibility == "public",
            Post.user_id == viewer_id,
        )
    base_q = base_q.filter(visibility_cond)

    if cursor is not None:
        c_dt, c_id = _decode_cursor(cursor)
        c_dt_str = c_dt.strftime("%Y-%m-%d %H:%M:%S")
        from sqlalchemy import text

        base_q = base_q.filter(
            text(
                "(strftime('%Y-%m-%d %H:%M:%S', posts.created_at) < :c_dt_str "
                "OR (strftime('%Y-%m-%d %H:%M:%S', posts.created_at) = :c_dt_str "
                "AND posts.id < :c_id))"
            ).bindparams(c_dt_str=c_dt_str, c_id=c_id)
        )

    base_q = base_q.order_by(Post.created_at.desc(), Post.id.desc())
    rows = base_q.limit(limit + 1).all()

    has_more = len(rows) > limit
    posts = rows[:limit]
    items = _posts_to_out(db, posts, viewer_id)

    next_cursor: str | None = None
    if has_more and posts:
        last = posts[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return FeedOut(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    ).model_dump(mode="json")


def get_post(db: Session, viewer_id: int, post_id: int) -> dict:
    post = db.query(Post).filter(Post.id == post_id, Post.deleted_at.is_(None)).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "Post not found", 404)
    if not can_view_post(db, viewer_id, post):
        raise AppError(ErrorCode.FORBIDDEN, "No permission to view this post", 403)
    return post_to_out(db, post, viewer_id=viewer_id)


def delete_post(db: Session, user: User, post_id: int) -> None:
    post = db.query(Post).filter(Post.id == post_id, Post.deleted_at.is_(None)).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "Post not found", 404)
    if post.user_id != user.id and user.role != "admin":
        raise AppError(ErrorCode.FORBIDDEN, "No permission to delete this post", 403)
    post.deleted_at = datetime.now(UTC)
    db.commit()


def get_user_posts(
    db: Session,
    viewer_id: int,
    target_user_id: int,
    cursor: str | None,
    limit: int = 20,
) -> dict:
    from app.utils.friends import are_friends

    base_q = db.query(Post).filter(
        Post.user_id == target_user_id,
        Post.deleted_at.is_(None),
    )

    if target_user_id != viewer_id:
        is_friend = are_friends(db, viewer_id, target_user_id)
        if is_friend:
            base_q = base_q.filter(
                or_(
                    Post.visibility == "public",
                    Post.visibility == "friends",
                )
            )
        else:
            base_q = base_q.filter(Post.visibility == "public")

    if cursor is not None:
        c_dt, c_id = _decode_cursor(cursor)
        c_dt_str = c_dt.strftime("%Y-%m-%d %H:%M:%S")
        from sqlalchemy import text

        base_q = base_q.filter(
            text(
                "(strftime('%Y-%m-%d %H:%M:%S', posts.created_at) < :c_dt_str "
                "OR (strftime('%Y-%m-%d %H:%M:%S', posts.created_at) = :c_dt_str "
                "AND posts.id < :c_id))"
            ).bindparams(c_dt_str=c_dt_str, c_id=c_id)
        )

    base_q = base_q.order_by(Post.created_at.desc(), Post.id.desc())
    rows = base_q.limit(limit + 1).all()

    has_more = len(rows) > limit
    posts = rows[:limit]
    items = _posts_to_out(db, posts, viewer_id)

    next_cursor: str | None = None
    if has_more and posts:
        last = posts[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return UserPostsOut(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    ).model_dump(mode="json")
