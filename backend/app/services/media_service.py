"""媒体服务：上传、媒体访问鉴权。"""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import get_storage_root, settings
from app.models.file_metadata import FileMetadata
from app.models.post_media import PostMedia
from app.models.users import User
from app.schemas.common import AppError, ErrorCode
from app.storage import filekit


def upload_media(db: Session, user: User, file: UploadFile) -> dict:
    """通用上传：校验 -> 同步落盘 -> 写 PostMedia(未绑定) + FileMetadata -> 返回。

    后台任务由路由触发。
    """
    if not file.filename:
        raise AppError(ErrorCode.VALIDATION_ERROR, "No file provided", 400)
    file.file.seek(0)
    content = file.file.read()
    max_any = max(settings.MEDIA_IMAGE_MAX_MB, settings.MEDIA_VIDEO_MAX_MB) * 1024 * 1024
    if len(content) > max_any:
        raise AppError(ErrorCode.FILE_TOO_LARGE, "File too large", 413)
    kind = filekit.detect_kind(content)
    filekit.check_size(kind, len(content))
    if kind == "image":
        fmt, _img = filekit.validate_image(content)
        if fmt == "jpg":
            fmt = "jpeg"
        mime = f"image/{fmt}"
    else:
        fmt = filekit.validate_video(content)
        mime = f"video/{fmt}"
    media_dir = filekit.get_media_dir()
    filename = filekit.generate_filename(fmt)
    abs_path = filekit.safe_save_bytes(media_dir, filename, content)
    storage_root = get_storage_root()
    rel_path = str(abs_path.relative_to(storage_root))
    media = PostMedia(
        post_id=None,
        owner_id=user.id,
        file_path=rel_path,
        thumb_path=None,
        large_path=None,
        filename=filename,
        size=len(content),
        mime=mime,
        format=fmt,
        kind=kind,
        sort_order=0,
    )
    db.add(media)
    db.flush()
    db.add(
        FileMetadata(
            storage_path=rel_path,
            original_name=file.filename or filename,
            filename=filename,
            size=len(content),
            mime=mime,
            format=fmt,
            kind=kind,
            owner_id=user.id,
        )
    )
    db.commit()
    db.refresh(media)
    return {
        "media_id": media.id,
        "kind": media.kind,
        "format": media.format,
        "size": media.size,
        "status": "pending",
        "created_at": media.created_at,
    }


def get_media_file(
    db: Session, viewer_id: int | None, post_id: int, media_id: int, spec: str
) -> tuple[Path, str]:
    """鉴权 + 防穿越，返回 (abs_path, content_type)。失败抛 AppError。"""
    if spec not in ("thumb", "large", "original"):
        raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid spec", 400)
    from app.models.posts import Post
    from app.utils.visibility import can_view_post

    post = db.query(Post).filter(Post.id == post_id, Post.deleted_at.is_(None)).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "Post not found", 404)
    if not can_view_post(db, viewer_id, post):
        raise AppError(ErrorCode.FORBIDDEN, "No permission to view this media", 403)
    media = (
        db.query(PostMedia).filter(PostMedia.id == media_id, PostMedia.post_id == post_id).first()
    )
    if not media:
        raise AppError(ErrorCode.NOT_FOUND, "Media not found", 404)
    if spec == "original":
        rel: str | None = media.file_path
        mime = media.mime
    elif spec == "thumb":
        rel = media.thumb_path
        mime = "image/webp"
    else:
        rel = media.large_path
        mime = "image/webp"
    if not rel:
        raise AppError(ErrorCode.MEDIA_NOT_READY, "Media not ready yet", 404)
    abs_path = filekit.resolve_within_storage(rel)
    if not abs_path:
        raise AppError(ErrorCode.NOT_FOUND, "File not found", 404)
    return abs_path, mime
