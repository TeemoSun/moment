"""好友路由：请求、列表、接受、拒绝、好友列表、删除好友。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, verify_csrf
from app.database import get_db
from app.models.users import User
from app.schemas.bot import BotPublicOut
from app.schemas.friend import (
    FriendOut,
    FriendRequestActionOut,
    FriendRequestIn,
    FriendRequestOut,
)
from app.services import bot_service, friend_service

router = APIRouter()


@router.post("/request", response_model=FriendRequestActionOut)
def send_request(
    data: FriendRequestIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return friend_service.request_friend(db, current_user, data.model_dump(mode="json"))


@router.get("/requests", response_model=list[FriendRequestOut])
def list_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return friend_service.list_requests(db, current_user)


@router.post("/requests/{request_id}/accept", response_model=FriendRequestActionOut)
def accept_request(
    request_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return friend_service.accept_request(db, current_user, request_id)


@router.post("/requests/{request_id}/reject", response_model=FriendRequestActionOut)
def reject_request(
    request_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return friend_service.reject_request(db, current_user, request_id)


@router.get("", response_model=list[FriendOut])
def list_friends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return friend_service.list_friends(db, current_user)


@router.delete("/{user_id}", status_code=204)
def remove_friend(
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> Response:
    friend_service.remove_friend(db, current_user, user_id)
    return Response(status_code=204)


@router.get("/bots", response_model=list[BotPublicOut])
def list_bots(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return bot_service.list_bots_public(db, current_user)


@router.post("/bots/{bot_user_id}", response_model=FriendRequestActionOut)
def add_bot_friend(
    bot_user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return bot_service.add_bot_friend(db, current_user, bot_user_id)
