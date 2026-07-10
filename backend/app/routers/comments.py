from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.permissions import can_view_post
from app.database import get_db
from app.deps import get_current_user
from app.models import Comment, Post, Reaction, User
from app.schemas import (
    CommentCreate, CommentOut, CommentTree, MessageOut, Paginated, ReplyCreate,
    UserBrief,
)

settings = get_settings()
router = APIRouter(tags=["comments"])


def _user_brief(user: User) -> UserBrief:
    return UserBrief(
        id=user.id, username=user.username, display_name=user.display_name,
        avatar_url=f"/api/media/avatar/{user.id}" if user.avatar_media_id else None,
    )


async def _comment_to_out(
    c: Comment, db: AsyncSession, viewer: User
) -> CommentOut:
    author = await db.get(User, c.user_id)
    reply_to_user = None
    if c.reply_to_user_id:
        r = await db.get(User, c.reply_to_user_id)
        if r:
            reply_to_user = _user_brief(r)

    reply_count_q = await db.execute(
        select(func.count(Comment.id)).where(
            Comment.parent_id == c.id, Comment.deleted_at.is_(None)
        )
    )
    reply_count = reply_count_q.scalar_one()

    like_count_q = await db.execute(
        select(func.count(Reaction.id)).where(
            Reaction.comment_id == c.id, Reaction.type == "like"
        )
    )
    like_count = like_count_q.scalar_one()

    liked_q = await db.execute(
        select(Reaction).where(
            Reaction.comment_id == c.id, Reaction.user_id == viewer.id,
            Reaction.type == "like",
        )
    )
    liked = liked_q.scalar_one_or_none() is not None

    return CommentOut(
        id=c.id,
        post_id=c.post_id,
        user=_user_brief(author),
        parent_id=c.parent_id,
        root_id=c.root_id,
        reply_to_user=reply_to_user,
        depth=c.depth,
        content=c.content,
        created_at=c.created_at,
        deleted=c.deleted_at is not None,
        reply_count=reply_count,
        like_count=like_count,
        liked=liked,
    )


async def _get_viewable_post(
    post_id: str, user: User, db: AsyncSession
) -> Post:
    post = await db.get(Post, post_id)
    if post is None or post.deleted_at is not None:
        raise HTTPException(404, "Post not found")
    if not await can_view_post(db, user, post):
        raise HTTPException(403, "Not allowed to view this post")
    return post


@router.post("/api/posts/{post_id}/comments", response_model=CommentOut, status_code=201)
async def create_comment(
    post_id: str,
    body: CommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_viewable_post(post_id, user, db)

    if body.parent_id is None:
        comment = Comment(
            post_id=post_id,
            user_id=user.id,
            parent_id=None,
            root_id="",
            reply_to_user_id=body.reply_to_user_id,
            depth=0,
            content=body.content,
        )
        db.add(comment)
        await db.flush()
        comment.root_id = comment.id
        if not comment.reply_to_user_id:
            comment.reply_to_user_id = (await db.get(Post, post_id)).user_id
        await db.flush()
        return await _comment_to_out(comment, db, user)

    parent = await db.get(Comment, body.parent_id)
    if parent is None or parent.deleted_at is not None:
        raise HTTPException(404, "Parent comment not found")
    if parent.post_id != post_id:
        raise HTTPException(400, "Parent comment belongs to another post")
    if parent.depth >= settings.MAX_COMMENT_DEPTH:
        raise HTTPException(400, f"Max comment depth ({settings.MAX_COMMENT_DEPTH}) reached")

    comment = Comment(
        post_id=post_id,
        user_id=user.id,
        parent_id=parent.id,
        root_id=parent.root_id,
        reply_to_user_id=body.reply_to_user_id or parent.user_id,
        depth=parent.depth + 1,
        content=body.content,
    )
    db.add(comment)
    await db.flush()
    return await _comment_to_out(comment, db, user)


@router.post("/api/comments/{comment_id}/replies", response_model=CommentOut, status_code=201)
async def create_reply(
    comment_id: str,
    body: ReplyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    parent = await db.get(Comment, comment_id)
    if parent is None or parent.deleted_at is not None:
        raise HTTPException(404, "Comment not found")
    await _get_viewable_post(parent.post_id, user, db)
    if parent.depth >= settings.MAX_COMMENT_DEPTH:
        raise HTTPException(400, f"Max comment depth ({settings.MAX_COMMENT_DEPTH}) reached")

    comment = Comment(
        post_id=parent.post_id,
        user_id=user.id,
        parent_id=parent.id,
        root_id=parent.root_id,
        reply_to_user_id=body.reply_to_user_id or parent.user_id,
        depth=parent.depth + 1,
        content=body.content,
    )
    db.add(comment)
    await db.flush()
    return await _comment_to_out(comment, db, user)


@router.get("/api/posts/{post_id}/comments", response_model=Paginated[CommentTree])
async def list_comments(
    post_id: str,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_viewable_post(post_id, user, db)

    roots_q = await db.execute(
        select(Comment)
        .where(Comment.post_id == post_id, Comment.depth == 0, Comment.deleted_at.is_(None))
        .order_by(Comment.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    roots = roots_q.scalars().all()

    trees = []
    for root in roots:
        replies_q = await db.execute(
            select(Comment).where(
                Comment.root_id == root.id,
                Comment.depth > 0,
                Comment.deleted_at.is_(None),
            ).order_by(Comment.created_at.asc())
        )
        replies = replies_q.scalars().all()
        total_q = await db.execute(
            select(func.count(Comment.id)).where(
                Comment.root_id == root.id, Comment.depth > 0,
                Comment.deleted_at.is_(None),
            )
        )
        total = total_q.scalar_one()
        trees.append(CommentTree(
            root=await _comment_to_out(root, db, user),
            replies=[await _comment_to_out(r, db, user) for r in replies],
            total_replies=total,
        ))

    total_roots_q = await db.execute(
        select(func.count(Comment.id)).where(
            Comment.post_id == post_id, Comment.depth == 0, Comment.deleted_at.is_(None)
        )
    )
    total = total_roots_q.scalar_one()
    return Paginated[CommentTree](
        items=trees, total=total, page=page, page_size=page_size,
        has_more=((page - 1) * page_size + page_size) < total,
    )


@router.get("/api/comments/{comment_id}/replies", response_model=Paginated[CommentOut])
async def list_replies(
    comment_id: str,
    page: int = 1,
    page_size: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    parent = await db.get(Comment, comment_id)
    if parent is None:
        raise HTTPException(404, "Comment not found")
    await _get_viewable_post(parent.post_id, user, db)

    q = await db.execute(
        select(Comment)
        .where(Comment.parent_id == comment_id, Comment.deleted_at.is_(None))
        .order_by(Comment.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [await _comment_to_out(c, db, user) for c in q.scalars().all()]
    total_q = await db.execute(
        select(func.count(Comment.id)).where(
            Comment.parent_id == comment_id, Comment.deleted_at.is_(None)
        )
    )
    total = total_q.scalar_one()
    return Paginated[CommentOut](
        items=items, total=total, page=page, page_size=page_size,
        has_more=((page - 1) * page_size + page_size) < total,
    )


@router.delete("/api/comments/{comment_id}", response_model=MessageOut)
async def delete_comment(
    comment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(404, "Comment not found")
    post = await db.get(Post, comment.post_id)
    if comment.user_id != user.id and (post is None or post.user_id != user.id):
        raise HTTPException(403, "Not allowed")
    comment.deleted_at = __import__("datetime").datetime.utcnow()
    comment.content = ""
    await db.flush()
    return MessageOut(message="Comment deleted")


@router.post("/api/posts/{post_id}/likes", response_model=MessageOut, status_code=201)
async def like_post(
    post_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_viewable_post(post_id, user, db)
    existing = await db.execute(
        select(Reaction).where(
            Reaction.post_id == post_id, Reaction.user_id == user.id,
            Reaction.type == "like",
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(Reaction(post_id=post_id, user_id=user.id, type="like"))
        await db.flush()
    return MessageOut(message="Liked")


@router.delete("/api/posts/{post_id}/likes", response_model=MessageOut)
async def unlike_post(
    post_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reaction).where(
            Reaction.post_id == post_id, Reaction.user_id == user.id,
            Reaction.type == "like",
        )
    )
    r = result.scalar_one_or_none()
    if r is not None:
        await db.delete(r)
        await db.flush()
    return MessageOut(message="Unliked")


@router.post("/api/comments/{comment_id}/likes", response_model=MessageOut, status_code=201)
async def like_comment(
    comment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(404, "Comment not found")
    await _get_viewable_post(comment.post_id, user, db)
    existing = await db.execute(
        select(Reaction).where(
            Reaction.comment_id == comment_id, Reaction.user_id == user.id,
            Reaction.type == "like",
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(Reaction(comment_id=comment_id, user_id=user.id, type="like"))
        await db.flush()
    return MessageOut(message="Liked")


@router.delete("/api/comments/{comment_id}/likes", response_model=MessageOut)
async def unlike_comment(
    comment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reaction).where(
            Reaction.comment_id == comment_id, Reaction.user_id == user.id,
            Reaction.type == "like",
        )
    )
    r = result.scalar_one_or_none()
    if r is not None:
        await db.delete(r)
        await db.flush()
    return MessageOut(message="Unliked")