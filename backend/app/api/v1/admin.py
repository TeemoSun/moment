"""管理后台路由：统计、用户/动态/评论/邀请码管理。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import require_admin, verify_csrf
from app.database import get_db
from app.schemas.admin import (
    AdminCommentListOut,
    AdminInviteListOut,
    AdminPostListOut,
    AdminUserListOut,
    AdminUserOut,
    AdminUserUpdateIn,
    StatsOut,
)
from app.schemas.invite import InviteActionOut
from app.services import admin_service

router = APIRouter()


@router.get("/stats", response_model=StatsOut)
def get_stats(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> dict:
    return admin_service.get_stats(db)


@router.get("/users", response_model=AdminUserListOut)
def list_users(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> dict:
    return admin_service.list_users(db, page, page_size, search)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    data: AdminUserUpdateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    admin=Depends(require_admin),
) -> dict:
    return admin_service.update_user(db, user_id, data)


@router.get("/posts", response_model=AdminPostListOut)
def list_posts(
    user_id: int | None = Query(default=None),
    visibility: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> dict:
    return admin_service.list_posts(db, page, page_size, user_id, visibility)


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    admin=Depends(require_admin),
) -> Response:
    admin_service.delete_post(db, post_id)
    return Response(status_code=204)


@router.get("/comments", response_model=AdminCommentListOut)
def list_comments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> dict:
    return admin_service.list_comments(db, page, page_size)


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    admin=Depends(require_admin),
) -> Response:
    admin_service.delete_comment(db, comment_id)
    return Response(status_code=204)


@router.get("/invites", response_model=AdminInviteListOut)
def list_invites(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> dict:
    return admin_service.list_invites(db, page, page_size)


@router.post("/invites/{invite_id}/revoke", response_model=InviteActionOut)
def revoke_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    admin=Depends(require_admin),
) -> dict:
    return admin_service.revoke_invite(db, invite_id)
