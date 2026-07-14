"""评论与点赞路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_optional_user, verify_csrf
from app.database import get_db
from app.models.users import User
from app.schemas.comment import (
    CommentCreateIn,
    CommentListOut,
    CommentMediaOut,
    CommentOut,
    LikeCountOut,
)
from app.services import comment_service, like_service

router = APIRouter()


@router.get("/posts/{post_id}/comments", response_model=CommentListOut)
def list_comments(
    post_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return comment_service.list_comments(db, current_user.id, post_id, page, page_size)


@router.post("/posts/{post_id}/comments", response_model=CommentOut, status_code=201)
def create_comment(
    post_id: int,
    data: CommentCreateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return comment_service.create_comment(db, current_user, post_id, data.model_dump())


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> Response:
    comment_service.delete_comment(db, current_user, comment_id)
    return Response(status_code=204)


@router.post("/comments/{comment_id}/likes", response_model=LikeCountOut)
def like_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return like_service.toggle_comment_like(db, current_user, comment_id)


@router.delete("/comments/{comment_id}/likes", response_model=LikeCountOut)
def unlike_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return like_service.unlike_comment(db, current_user, comment_id)


@router.post("/posts/{post_id}/likes", response_model=LikeCountOut)
def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return like_service.toggle_post_like(db, current_user, post_id)


@router.delete("/posts/{post_id}/likes", response_model=LikeCountOut)
def unlike_post(
    post_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return like_service.unlike_post(db, current_user, post_id)


@router.post("/comments/media", response_model=CommentMediaOut)
def upload_comment_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    return comment_service.upload_comment_image(db, current_user, file)


@router.get("/comments/{comment_id}/media/{spec}")
def get_comment_media(
    comment_id: int,
    spec: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> FileResponse:
    path, content_type = comment_service.get_comment_image(
        db, current_user.id if current_user else None, comment_id, spec
    )
    return FileResponse(
        path, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"}
    )
