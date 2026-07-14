"""管理后台服务：统计、用户/动态/评论/邀请码管理。"""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.comments import Comment
from app.models.invite_codes import InviteCode
from app.models.likes import Like
from app.models.posts import Post
from app.models.users import User
from app.schemas.admin import (
    AdminAuthorOut,
    AdminCommentListOut,
    AdminCommentOut,
    AdminInviteListOut,
    AdminInviteOut,
    AdminPostListOut,
    AdminPostOut,
    AdminUserListOut,
    AdminUserOut,
    AdminUserUpdateIn,
    StatsOut,
)
from app.schemas.common import AppError, ErrorCode
from app.services.user_service import avatar_url_for
from app.utils.time import utcnow


def _build_admin_author(user: User) -> dict:
    is_deactivated = user.status == "deactivated"
    if is_deactivated:
        return AdminAuthorOut(
            id=user.id,
            email=user.email,
            nickname="已注销",
            avatar_url="/api/v1/avatars/default",
            is_deactivated=True,
        ).model_dump(mode="json")
    return AdminAuthorOut(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        avatar_url=avatar_url_for(user),
        is_deactivated=False,
    ).model_dump(mode="json")


def _user_to_admin_out(user: User) -> dict:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        role=user.role,
        status=user.status,
        can_invite=user.can_invite,
        avatar_url=avatar_url_for(user),
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    ).model_dump(mode="json")


def get_stats(db: Session) -> dict:
    user_count = db.query(func.count(User.id)).scalar() or 0
    post_count = db.query(func.count(Post.id)).filter(Post.deleted_at.is_(None)).scalar() or 0
    comment_count = (
        db.query(func.count(Comment.id)).filter(Comment.deleted_at.is_(None)).scalar() or 0
    )
    like_count = db.query(func.count(Like.id)).scalar() or 0
    invite_count = db.query(func.count(InviteCode.id)).scalar() or 0
    used_invite_count = (
        db.query(func.count(InviteCode.id)).filter(InviteCode.status == "used").scalar() or 0
    )
    return StatsOut(
        user_count=user_count,
        post_count=post_count,
        comment_count=comment_count,
        like_count=like_count,
        invite_count=invite_count,
        used_invite_count=used_invite_count,
    ).model_dump(mode="json")


def list_users(db: Session, page: int, page_size: int, search: str | None) -> dict:
    base_q = db.query(User)
    if search:
        pattern = f"%{search}%"
        base_q = base_q.filter(or_(User.email.ilike(pattern), User.nickname.ilike(pattern)))
    total = base_q.count()
    offset = (page - 1) * page_size
    users = base_q.order_by(User.id.asc()).offset(offset).limit(page_size).all()
    items = [_user_to_admin_out(u) for u in users]
    has_more = offset + page_size < total
    return AdminUserListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    ).model_dump(mode="json")


def update_user(db: Session, user_id: int, data: AdminUserUpdateIn) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppError(ErrorCode.USER_NOT_FOUND, "User not found", 404)

    if data.restore is True:
        if user.status == "deactivated":
            user.status = "active"

    if data.status is not None:
        if user.status == "deactivated":
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Cannot set deactivated via admin; use restore",
                400,
            )
        user.status = data.status

    if data.can_invite is not None:
        user.can_invite = data.can_invite

    db.commit()
    db.refresh(user)
    return _user_to_admin_out(user)


def list_posts(
    db: Session,
    page: int,
    page_size: int,
    user_id: int | None,
    visibility: str | None,
) -> dict:
    base_q = db.query(Post)
    if user_id is not None:
        base_q = base_q.filter(Post.user_id == user_id)
    if visibility is not None:
        base_q = base_q.filter(Post.visibility == visibility)
    total = base_q.count()
    offset = (page - 1) * page_size
    posts = (
        base_q.order_by(Post.created_at.desc(), Post.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    if not posts:
        return AdminPostListOut(
            items=[],
            total=total,
            page=page,
            page_size=page_size,
            has_more=False,
        ).model_dump(mode="json")

    author_ids = list({p.user_id for p in posts})
    authors = {u.id: u for u in db.query(User).filter(User.id.in_(author_ids)).all()}

    post_ids = [p.id for p in posts]
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

    items: list[dict] = []
    for p in posts:
        author = authors.get(p.user_id)
        assert author is not None
        items.append(
            AdminPostOut(
                id=p.id,
                content=p.content,
                visibility=p.visibility,
                deleted=p.deleted_at is not None,
                author=_build_admin_author(author),
                like_count=like_counts.get(p.id, 0),
                comment_count=comment_counts.get(p.id, 0),
                created_at=p.created_at,
                deleted_at=p.deleted_at,
            ).model_dump(mode="json")
        )

    has_more = offset + page_size < total
    return AdminPostListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    ).model_dump(mode="json")


def delete_post(db: Session, post_id: int) -> None:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "Post not found", 404)
    if post.deleted_at is not None:
        return
    post.deleted_at = utcnow()
    db.commit()


def list_comments(db: Session, page: int, page_size: int) -> dict:
    base_q = db.query(Comment)
    total = base_q.count()
    offset = (page - 1) * page_size
    comments = (
        base_q.order_by(Comment.created_at.desc(), Comment.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    if not comments:
        return AdminCommentListOut(
            items=[],
            total=total,
            page=page,
            page_size=page_size,
            has_more=False,
        ).model_dump(mode="json")

    author_ids = list({c.user_id for c in comments})
    authors = {u.id: u for u in db.query(User).filter(User.id.in_(author_ids)).all()}

    comment_ids = [c.id for c in comments]
    like_counts_rows = (
        db.query(Like.target_id, func.count(Like.id))
        .filter(Like.target_type == "comment", Like.target_id.in_(comment_ids))
        .group_by(Like.target_id)
        .all()
    )
    like_counts = {row[0]: row[1] for row in like_counts_rows}

    items: list[dict] = []
    for c in comments:
        author = authors.get(c.user_id)
        assert author is not None
        image_thumb_url = f"/api/v1/comments/{c.id}/media/thumb" if c.image_thumb_path else None
        items.append(
            AdminCommentOut(
                id=c.id,
                post_id=c.post_id,
                content=c.content,
                image_thumb_url=image_thumb_url,
                deleted=c.deleted_at is not None,
                author=_build_admin_author(author),
                like_count=like_counts.get(c.id, 0),
                created_at=c.created_at,
                deleted_at=c.deleted_at,
            ).model_dump(mode="json")
        )

    has_more = offset + page_size < total
    return AdminCommentListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    ).model_dump(mode="json")


def delete_comment(db: Session, comment_id: int) -> None:
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise AppError(ErrorCode.COMMENT_NOT_FOUND, "Comment not found", 404)
    if comment.deleted_at is not None:
        return
    comment.deleted_at = utcnow()
    db.commit()


def list_invites(db: Session, page: int, page_size: int) -> dict:
    base_q = db.query(InviteCode)
    total = base_q.count()
    offset = (page - 1) * page_size
    invites = base_q.order_by(InviteCode.created_at.desc()).offset(offset).limit(page_size).all()

    if not invites:
        return AdminInviteListOut(
            items=[],
            total=total,
            page=page,
            page_size=page_size,
            has_more=False,
        ).model_dump(mode="json")

    creator_ids = list({i.creator_id for i in invites})
    creators = {u.id: u for u in db.query(User).filter(User.id.in_(creator_ids)).all()}

    items: list[dict] = []
    for i in invites:
        creator = creators.get(i.creator_id)
        assert creator is not None
        items.append(
            AdminInviteOut(
                id=i.id,
                code=i.code,
                status=i.status,
                expires_at=i.expires_at,
                created_at=i.created_at,
                used_by_id=i.used_by_id,
                creator=_build_admin_author(creator),
            ).model_dump(mode="json")
        )

    has_more = offset + page_size < total
    return AdminInviteListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    ).model_dump(mode="json")


def revoke_invite(db: Session, invite_id: int) -> dict:
    invite = db.query(InviteCode).filter(InviteCode.id == invite_id).first()
    if not invite:
        raise AppError(ErrorCode.INVITE_NOT_FOUND, "Invite not found", 404)
    if invite.status == "used":
        raise AppError(ErrorCode.INVITE_ALREADY_USED, "Used invite cannot be revoked", 400)
    if invite.status in ("revoked", "expired"):
        return {"message": "Invite already inactive"}
    invite.status = "revoked"
    db.commit()
    return {"message": "Invite revoked"}
