from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import Friendship, User
from app.schemas import FriendOut, FriendRequestOut, MessageOut

router = APIRouter(prefix="/api/friends", tags=["friends"])


def _user_brief(user: User):
    from app.schemas import UserBrief
    return UserBrief(
        id=user.id, username=user.username, display_name=user.display_name,
        avatar_url=f"/api/media/avatar/{user.id}?v={user.avatar_media_id}" if user.avatar_media_id else None,
    )


@router.get("/requests", response_model=list[FriendRequestOut])
async def list_requests(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship).where(
            Friendship.addressee_id == user.id,
            Friendship.status == "pending",
        )
    )
    items = result.scalars().all()
    out = []
    for f in items:
        requester = await db.get(User, f.requester_id)
        out.append(FriendRequestOut(
            id=f.id, requester=_user_brief(requester),
            addressee_id=f.addressee_id, status=f.status, created_at=f.created_at,
        ))
    return out


@router.post("/requests/{target_username}", response_model=MessageOut, status_code=201)
async def send_request(
    target_username: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if target_username == user.username:
        raise HTTPException(400, "Cannot friend yourself")
    result = await db.execute(select(User).where(User.username == target_username))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(404, "User not found")

    existing = await db.execute(
        select(Friendship).where(
            (
                (Friendship.requester_id == user.id and Friendship.addressee_id == target.id)
                | (Friendship.requester_id == target.id and Friendship.addressee_id == user.id)
            )
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(409, "Friendship already exists or pending")

    fs = Friendship(requester_id=user.id, addressee_id=target.id, status="pending")
    db.add(fs)
    await db.flush()
    return MessageOut(message="Request sent")


@router.post("/requests/{request_id}/accept", response_model=MessageOut)
async def accept_request(
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fs = await db.get(Friendship, request_id)
    if fs is None or fs.addressee_id != user.id:
        raise HTTPException(404, "Request not found")
    if fs.status != "pending":
        raise HTTPException(400, "Request already handled")
    fs.status = "accepted"
    fs.accepted_at = datetime.utcnow()
    await db.flush()
    return MessageOut(message="Request accepted")


@router.post("/requests/{request_id}/reject", response_model=MessageOut)
async def reject_request(
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fs = await db.get(Friendship, request_id)
    if fs is None or fs.addressee_id != user.id:
        raise HTTPException(404, "Request not found")
    if fs.status != "pending":
        raise HTTPException(400, "Request already handled")
    await db.delete(fs)
    await db.flush()
    return MessageOut(message="Request rejected")


@router.get("", response_model=list[FriendOut])
async def list_friends(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship).where(
            Friendship.status == "accepted",
            (Friendship.requester_id == user.id) | (Friendship.addressee_id == user.id),
        )
    )
    items = result.scalars().all()
    out = []
    for f in items:
        other_id = f.addressee_id if f.requester_id == user.id else f.requester_id
        other = await db.get(User, other_id)
        out.append(FriendOut(
            id=f.id, user=_user_brief(other), status=f.status,
            accepted_at=f.accepted_at,
        ))
    return out


@router.delete("/{target_user_id}", response_model=MessageOut)
async def delete_friend(
    target_user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship).where(
            Friendship.status == "accepted",
            (
                (Friendship.requester_id == user.id and Friendship.addressee_id == target_user_id)
                | (Friendship.requester_id == target_user_id and Friendship.addressee_id == user.id)
            ),
        )
    )
    fs = result.scalar_one_or_none()
    if fs is None:
        raise HTTPException(404, "Friendship not found")
    await db.delete(fs)
    await db.flush()
    return MessageOut(message="Friend removed")