from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.file_validator import FileValidationError, get_image_dimensions, validate_upload
from app.core.thumbnail import (
    generate_image_thumbnails, generate_video_thumbnail, get_video_duration,
)
from app.logging_conf import logger
from app.models import Media, Post, User

settings = get_settings()


def _bucket_dir() -> Path:
    now = datetime.utcnow()
    return Path(settings.upload_path) / f"{now.year}" / f"{now:02m}"


async def _read_head(file: UploadFile, n: int = 262144) -> bytes:
    await file.seek(0)
    head = await file.read(n)
    await file.seek(0)
    return head


async def save_upload(file: UploadFile, user: User, db: AsyncSession) -> Media:
    head = await _read_head(file)
    filename = file.filename or "upload"

    try:
        media_type, real_ext = validate_upload(
            head, filename, 0,
            settings.max_image_bytes, settings.max_video_bytes,
        )
    except FileValidationError as e:
        raise HTTPException(400, str(e))

    bucket = _bucket_dir()
    bucket.mkdir(parents=True, exist_ok=True)
    thumb_dir = bucket / "thumbs"
    stored_name = f"{uuid.uuid4().hex}.{real_ext}"
    stored_path = bucket / stored_name

    size_bytes = 0
    content = head
    size_bytes += len(content)
    with open(stored_path, "wb") as f:
        f.write(content)
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size_bytes += len(chunk)
            if media_type == "image" and size_bytes > settings.max_image_bytes:
                f.close()
                stored_path.unlink(missing_ok=True)
                raise HTTPException(413, "Image too large")
            if media_type == "video" and size_bytes > settings.max_video_bytes:
                f.close()
                stored_path.unlink(missing_ok=True)
                raise HTTPException(413, "Video too large")
            f.write(chunk)

    base_name = stored_name.rsplit(".", 1)[0]
    thumb_small = thumb_medium = None
    width = height = None
    duration = None

    if media_type == "image":
        thumb_small, thumb_medium = generate_image_thumbnails(
            stored_path, thumb_dir, base_name
        )
        width, height = get_image_dimensions(str(stored_path))
    else:
        thumb_small = generate_video_thumbnail(stored_path, thumb_dir, base_name)
        duration = get_video_duration(stored_path)

    rel_path = str(stored_path.relative_to(Path(settings.upload_path)))
    media = Media(
        user_id=user.id,
        original_filename=filename,
        stored_filename=stored_name,
        relative_path=rel_path,
        mime_type=file.content_type or f"{media_type}/{real_ext}",
        file_format=real_ext,
        size_bytes=size_bytes,
        width=width,
        height=height,
        duration=duration,
        media_type=media_type,
        thumb_small_path=(
            str(Path(thumb_small).relative_to(Path(settings.upload_path)))
            if thumb_small else None
        ),
        thumb_medium_path=(
            str(Path(thumb_medium).relative_to(Path(settings.upload_path)))
            if thumb_medium else None
        ),
    )
    db.add(media)
    await db.flush()
    logger.info("Upload saved: media_id={} type={} size={}", media.id, media_type, size_bytes)
    return media


async def save_user_avatar(file: UploadFile, user: User, db: AsyncSession) -> Media:
    media = await save_upload(file, user, db)
    if media.media_type != "image":
        await db.delete(media)
        raise HTTPException(400, "Avatar must be an image")
    return media


def media_url(media_id: str, variant: str = "original") -> str:
    return f"/api/media/{media_id}/{variant}"


def resolve_media_path(media: Media, variant: str) -> Path:
    base = Path(settings.upload_path)
    if variant == "small" and media.thumb_small_path:
        return base / media.thumb_small_path
    if variant == "medium" and media.thumb_medium_path:
        return base / media.thumb_medium_path
    return base / media.relative_path


def delete_media_files(media: Media) -> None:
    base = Path(settings.upload_path)
    for p in [media.relative_path, media.thumb_small_path, media.thumb_medium_path]:
        if p:
            full = base / p
            full.unlink(missing_ok=True)