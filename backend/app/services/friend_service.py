"""好友服务：请求、接受、拒绝、列表、删除。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.friendships import Friendship
from app.models.users import User
from app.schemas.common import AppError, ErrorCode
from app.schemas.friend import FriendOut, FriendRequestOut, FriendUserBrief
from app.services.user_service import avatar_url_for
from app.utils.friends import are_friends


def _user_brief(user_obj: User) -> dict:
    if user_obj.status != "active":
        return FriendUserBrief(
            id=user_obj.id,
            nickname="已注销",
            avatar_url="/api/v1/avatars/default",
            is_deactivated=True,
        ).model_dump(mode="json")
    return FriendUserBrief(
        id=user_obj.id,
        nickname=user_obj.nickname,
        avatar_url=avatar_url_for(user_obj),
        is_deactivated=False,
    ).model_dump(mode="json")


def request_friend(db: Session, user: User, data: dict) -> dict:
    email = data["email"].lower().strip()
    target = db.query(User).filter(User.email == email).first()
    if not target:
        raise AppError(ErrorCode.USER_NOT_FOUND, "User not found", 404)
    if target.id == user.id:
        raise AppError(ErrorCode.CANNOT_FRIEND_SELF, "Cannot send friend request to yourself", 400)
    if target.status != "active":
        raise AppError(ErrorCode.USER_NOT_FOUND, "User not found", 404)
    if are_friends(db, user.id, target.id):
        raise AppError(ErrorCode.ALREADY_FRIENDS, "Already friends", 400)
    lo, hi = sorted((user.id, target.id))
    existing = (
        db.query(Friendship)
        .filter(
            Friendship.user_a_id == lo,
            Friendship.user_b_id == hi,
            Friendship.status == "pending",
        )
        .first()
    )
    if existing:
        raise AppError(ErrorCode.FRIEND_REQUEST_EXISTS, "Friend request already exists", 400)
    f = Friendship(
        user_a_id=lo,
        user_b_id=hi,
        status="pending",
        requester_id=user.id,
        created_at=datetime.now(UTC),
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return {"message": "Friend request sent"}


def list_requests(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(Friendship)
        .filter(
            Friendship.status == "pending",
            Friendship.requester_id != user.id,
            (Friendship.user_a_id == user.id) | (Friendship.user_b_id == user.id),
        )
        .all()
    )
    result: list[dict] = []
    for f in rows:
        other_id = f.user_b_id if f.user_a_id == user.id else f.user_a_id
        other = db.query(User).filter(User.id == other_id).first()
        if not other:
            continue
        result.append(
            FriendRequestOut(
                id=f.id,
                requester=FriendUserBrief(**_user_brief(other)),
                created_at=f.created_at,
            ).model_dump(mode="json")
        )
    return result


def accept_request(db: Session, user: User, request_id: int) -> dict:
    f = db.query(Friendship).filter(Friendship.id == request_id).first()
    if not f or f.status != "pending":
        raise AppError(ErrorCode.FRIEND_REQUEST_NOT_FOUND, "Friend request not found", 404)
    if f.requester_id == user.id or not (f.user_a_id == user.id or f.user_b_id == user.id):
        raise AppError(ErrorCode.FORBIDDEN, "No permission to accept this request", 403)
    f.status = "accepted"
    f.accepted_at = datetime.now(UTC)
    db.commit()
    return {"message": "Friend request accepted"}


def reject_request(db: Session, user: User, request_id: int) -> dict:
    f = db.query(Friendship).filter(Friendship.id == request_id).first()
    if not f or f.status != "pending":
        raise AppError(ErrorCode.FRIEND_REQUEST_NOT_FOUND, "Friend request not found", 404)
    if f.requester_id == user.id or not (f.user_a_id == user.id or f.user_b_id == user.id):
        raise AppError(ErrorCode.FORBIDDEN, "No permission to reject this request", 403)
    db.delete(f)
    db.commit()
    return {"message": "Friend request rejected"}


def list_friends(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(Friendship)
        .filter(
            Friendship.status == "accepted",
            (Friendship.user_a_id == user.id) | (Friendship.user_b_id == user.id),
        )
        .order_by(Friendship.accepted_at.desc())
        .all()
    )
    result: list[dict] = []
    for f in rows:
        other_id = f.user_b_id if f.user_a_id == user.id else f.user_a_id
        other = db.query(User).filter(User.id == other_id).first()
        if not other:
            continue
        since = f.accepted_at or f.created_at
        result.append(
            FriendOut(
                id=f.id,
                user=FriendUserBrief(**_user_brief(other)),
                since=since,
                requester_id=f.requester_id,
            ).model_dump(mode="json")
        )
    return result


def remove_friend(db: Session, user: User, other_id: int) -> None:
    if not are_friends(db, user.id, other_id):
        raise AppError(ErrorCode.NOT_FRIENDS, "Not friends", 400)
    lo, hi = sorted((user.id, other_id))
    f = (
        db.query(Friendship)
        .filter(
            Friendship.user_a_id == lo,
            Friendship.user_b_id == hi,
            Friendship.status == "accepted",
        )
        .first()
    )
    if f:
        db.delete(f)
        db.commit()


def get_friendship_status(db: Session, viewer_id: int, user_id: int) -> str:
    if viewer_id == user_id:
        return "self"
    if are_friends(db, viewer_id, user_id):
        return "friends"
    lo, hi = sorted((viewer_id, user_id))
    pending = (
        db.query(Friendship)
        .filter(
            Friendship.user_a_id == lo,
            Friendship.user_b_id == hi,
            Friendship.status == "pending",
        )
        .first()
    )
    if not pending:
        return "none"
    if pending.requester_id == viewer_id:
        return "pending_sent"
    return "pending_received"
