from __future__ import annotations

from datetime import datetime
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import can_view_post
from app.database import get_db
from app.deps import get_current_user
from app.models import Comment, Media, Post, Reaction, User
from app.routers.media import _media_out
from app.schemas import (
    MediaOut, MessageOut, Paginated, PostCreate, PostDetailOut, PostOut, PostUpdate,
    UserBrief,
)
from app.services.media_service import delete_media_files

router = APIRouter(tags=["posts"])


def _user_brief(user: User) -> UserBrief:
    return UserBrief(
        id=user.id, username=user.username, display_name=user.display_name,
        avatar_url=f"/api/media/avatar/{user.id}" if user.avatar_media_id else None,
    )


async def _post_to_out(
    post: Post, db: AsyncSession, viewer: User
) -> PostOut:
    post_user = await db.get(User, post.user_id)
    media_result = await db.execute(
        select(Media).where(Media.post_id == post.id)
    )
    media_items = media_result.scalars().all()

    comment_count_q = await db.execute(
        select(func.count(Comment.id)).where(
            Comment.post_id == post.id, Comment.deleted_at.is_(None)
        )
    )
    comment_count = comment_count_q.scalar_one()

    like_count_q = await db.execute(
        select(func.count(Reaction.id)).where(
            Reaction.post_id == post.id, Reaction.type == "like"
        )
    )
    like_count = like_count_q.scalar_one()

    liked_q = await db.execute(
        select(Reaction).where(
            Reaction.post_id == post.id, Reaction.user_id == viewer.id,
            Reaction.type == "like",
        )
    )
    liked = liked_q.scalar_one_or_none() is not None

    return PostOut(
        id=post.id,
        user=_user_brief(post_user),
        content=post.content,
        visibility=post.visibility,
        media=[_media_out(m) for m in media_items],
        comment_count=comment_count,
        like_count=like_count,
        liked=liked,
        created_at=post.created_at,
    )


@router.post("/api/posts", response_model=PostOut, status_code=201)
async def create_post(
    body: PostCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    media_items = []
    if body.media_ids:
        result = await db.execute(
            select(Media).where(
                Media.id.in_(body.media_ids), Media.user_id == user.id,
                Media.post_id.is_(None),
            )
        )
        media_items = result.scalars().all()
        if len(media_items) != len(body.media_ids):
            raise HTTPException(400, "Some media ids invalid or already attached")

    post = Post(
        user_id=user.id, content=body.content, visibility=body.visibility,
    )
    db.add(post)
    await db.flush()
    for m in media_items:
        m.post_id = post.id
    await db.flush()
    return await _post_to_out(post, db, user)


@router.get("/api/posts/feed", response_model=Paginated[PostOut])
async def get_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Post)
        .where(Post.deleted_at.is_(None))
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    posts = result.scalars().all()

    visible = []
    for post in posts:
        if await can_view_post(db, user, post):
            visible.append(post)

    total_q = await db.execute(
        select(func.count(Post.id)).where(Post.deleted_at.is_(None))
    )
    total = total_q.scalar_one()

    items = [await _post_to_out(p, db, user) for p in visible]
    return Paginated(
        items=items, total=total, page=page, page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.get("/api/posts/me", response_model=Paginated[PostOut])
async def get_my_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Post)
        .where(Post.user_id == user.id, Post.deleted_at.is_(None))
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    posts = result.scalars().all()
    items = [await _post_to_out(p, db, user) for p in posts]
    total_q = await db.execute(
        select(func.count(Post.id)).where(
            Post.user_id == user.id, Post.deleted_at.is_(None)
        )
    )
    total = total_q.scalar_one()
    return Paginated(
        items=items, total=total, page=page, page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.get("/api/posts/{post_id}", response_model=PostDetailOut)
async def get_post(
    post_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.deleted_at is not None:
        raise HTTPException(404, "Post not found")
    if not await can_view_post(db, user, post):
        raise HTTPException(403, "Not allowed to view this post")

    base = await _post_to_out(post, db, user)
    return PostDetailOut(**base.model_dump(), updated_at=post.updated_at, deleted_at=post.deleted_at)


@router.patch("/api/posts/{post_id}", response_model=PostOut)
async def update_post(
    post_id: str,
    body: PostUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.deleted_at is not None:
        raise HTTPException(404, "Post not found")
    if post.user_id != user.id:
        raise HTTPException(403, "Not allowed")
    if body.content is not None:
        post.content = body.content
    if body.visibility is not None:
        post.visibility = body.visibility
    await db.flush()
    return await _post_to_out(post, db, user)


@router.delete("/api/posts/{post_id}", response_model=MessageOut)
async def delete_post(
    post_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(404, "Post not found")
    if post.user_id != user.id:
        raise HTTPException(403, "Not allowed")
    post.deleted_at = datetime.utcnow()
    result = await db.execute(select(Media).where(Media.post_id == post_id))
    for m in result.scalars().all():
        delete_media_files(m)
    await db.flush()
    return MessageOut(message="Post deleted")