"""动态路由：创建、Feed、详情、删除、用户动态。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, verify_csrf
from app.database import get_db
from app.models.users import User
from app.schemas.post import FeedOut, PostCreateIn, PostDetailOut, PostOut, UserPostsOut
from app.services import post_service

router = APIRouter()


@router.post("/posts", response_model=PostOut, status_code=201)
def create_post(
    data: PostCreateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return post_service.create_post(db, current_user, data)


@router.get("/feed", response_model=FeedOut)
def get_feed(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return post_service.get_feed(db, current_user.id, cursor, limit)


@router.get("/posts/{post_id}", response_model=PostDetailOut)
def get_post_detail(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return post_service.get_post(db, current_user.id, post_id)


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> Response:
    post_service.delete_post(db, current_user, post_id)
    return Response(status_code=204)


@router.get("/users/{user_id}/posts", response_model=UserPostsOut)
def get_user_posts(
    user_id: int,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return post_service.get_user_posts(db, current_user.id, user_id, cursor, limit)
