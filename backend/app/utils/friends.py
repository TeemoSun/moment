"""好友关系工具。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.friendships import Friendship


def are_friends(db: Session, user_a_id: int, user_b_id: int) -> bool:
    """是否互为好友（accepted）。自己与自己视为 True（方便可见性判断）。"""
    if user_a_id == user_b_id:
        return True
    lo, hi = sorted((user_a_id, user_b_id))
    f = (
        db.query(Friendship)
        .filter(
            Friendship.user_a_id == lo,
            Friendship.user_b_id == hi,
            Friendship.status == "accepted",
        )
        .first()
    )
    return f is not None
