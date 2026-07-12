from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.permissions import can_view_post_of_user
from app.core.rate_limit import limiter
from app.database import get_db
from app.deps import get_current_user, get_current_user_for_media
from app.models import Media, Post, User
from app.schemas import MediaOut
from app.services.media_service import (
    media_url, resolve_media_path, save_upload,
)

settings = get_settings()
router = APIRouter(prefix="/api/media", tags=["media"])


def _media_out(media: Media) -> MediaOut:
    return MediaOut(
        id=media.id,
        media_type=media.media_type,
        mime_type=media.mime_type,
        file_format=media.file_format,
        size_bytes=media.size_bytes,
        width=media.width,
        height=media.height,
        duration=media.duration,
        original_filename=media.original_filename,
        small_url=media_url(media.id, "small") if media.thumb_small_path else None,
        medium_url=media_url(media.id, "medium") if media.thumb_medium_path else None,
        original_url=media_url(media.id, "original"),
    )


@router.post("", response_model=MediaOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_media(
    request: Request,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    media = await save_upload(file, user, db)
    return _media_out(media)


@router.get("/avatar/{user_id}", response_class=FileResponse)
async def get_avatar(
    user_id: str,
    user: User = Depends(get_current_user_for_media),
    db: AsyncSession = Depends(get_db),
):
    other = await db.get(User, user_id)
    if other is None:
        raise HTTPException(404, "User not found")
    if not other.avatar_media_id:
        raise HTTPException(404, "No avatar")
    media = await db.get(Media, other.avatar_media_id)
    if media is None:
        raise HTTPException(404, "Avatar media missing")
    path = resolve_media_path(media, "medium")
    if not path.exists():
        path = resolve_media_path(media, "original")
    if not path.exists():
        raise HTTPException(404, "Avatar file missing")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/{media_id}/{variant}", response_class=FileResponse)
async def get_media(
    media_id: str,
    variant: str,
    user: User = Depends(get_current_user_for_media),
    db: AsyncSession = Depends(get_db),
):
    if variant not in ("small", "medium", "original"):
        raise HTTPException(400, "Invalid variant")
    media = await db.get(Media, media_id)
    if media is None:
        raise HTTPException(404, "Media not found")

    if media.post_id is not None:
        post = await db.get(Post, media.post_id)
        if post is not None:
            allowed = await can_view_post_of_user(db, user, post.user_id, post.visibility)
            if not allowed:
                raise HTTPException(403, "Not allowed to view this media")
    else:
        if media.user_id != user.id:
            other = await db.get(User, media.user_id)
            if other and media.id == other.avatar_media_id:
                pass
            else:
                raise HTTPException(403, "Not allowed to view this media")

    path = resolve_media_path(media, variant)
    if not path.exists():
        raise HTTPException(404, "File not found on disk")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})