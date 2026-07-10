from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Friendship, Post, User


async def are_friends(db: AsyncSession, user_a: str, user_b: str) -> bool:
    if user_a == user_b:
        return True
    result = await db.execute(
        select(Friendship).where(
            Friendship.status == "accepted",
            (
                (Friendship.requester_id == user_a and Friendship.addressee_id == user_b)
                | (Friendship.requester_id == user_b and Friendship.addressee_id == user_a)
            ),
        )
    )
    return result.scalar_one_or_none() is not None


async def can_view_post(db: AsyncSession, viewer: User, post: Post) -> bool:
    if post.user_id == viewer.id:
        return True
    if post.visibility == "public":
        return True
    if post.visibility == "friends":
        return await are_friends(db, viewer.id, post.user_id)
    return False


async def can_view_post_of_user(
    db: AsyncSession, viewer: User, post_user_id: str, visibility: str
) -> bool:
    if viewer.id == post_user_id:
        return True
    if visibility == "public":
        return True
    if visibility == "friends":
        return await are_friends(db, viewer.id, post_user_id)
    return False