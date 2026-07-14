"""媒体服务：上传、媒体访问鉴权。"""

from __future__ import annotations

import os
import tempfile
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
    采用分块流式落盘，避免大文件全量读入内存。
    """
    if not file.filename:
        raise AppError(ErrorCode.VALIDATION_ERROR, "未提供文件", 400)

    max_any = max(settings.MEDIA_IMAGE_MAX_MB, settings.MEDIA_VIDEO_MAX_MB) * 1024 * 1024
    media_dir = filekit.get_media_dir()

    # 先流式落盘到临时文件（带大小上限校验）
    tmp_fd, tmp_name = tempfile.mkstemp(dir=media_dir, suffix=".tmp")
    tmp_path = Path(tmp_name)
    os.close(tmp_fd)
    try:
        total = filekit.stream_to_file(file.file, tmp_path, max_any)
    except AppError:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise AppError(ErrorCode.VALIDATION_ERROR, "读取上传文件失败", 400) from None

    # 从临时文件检测真实格式
    try:
        kind = filekit.detect_kind_from_file(tmp_path)
        filekit.check_size(kind, total)
        if kind == "image":
            fmt = filekit.validate_image_file(tmp_path)
            if fmt == "jpg":
                fmt = "jpeg"
            mime = f"image/{fmt}"
        else:
            fmt = filekit.validate_video_file(tmp_path)
            mime = f"video/{fmt}"
    except AppError:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise

    # 重命名为最终文件名
    filename = filekit.generate_filename(fmt)
    abs_path = media_dir / filename
    tmp_path.rename(abs_path)
    storage_root = get_storage_root()
    rel_path = str(abs_path.relative_to(storage_root))
    media = PostMedia(
        post_id=None,
        owner_id=user.id,
        file_path=rel_path,
        thumb_path=None,
        large_path=None,
        filename=filename,
        size=total,
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
            size=total,
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
        raise AppError(ErrorCode.VALIDATION_ERROR, "规格参数无效", 400)
    from app.models.posts import Post
    from app.utils.visibility import can_view_post

    post = db.query(Post).filter(Post.id == post_id, Post.deleted_at.is_(None)).first()
    if not post:
        raise AppError(ErrorCode.NOT_FOUND, "动态不存在", 404)
    if not can_view_post(db, viewer_id, post):
        raise AppError(ErrorCode.FORBIDDEN, "无权查看此媒体", 403)
    media = (
        db.query(PostMedia).filter(PostMedia.id == media_id, PostMedia.post_id == post_id).first()
    )
    if not media:
        raise AppError(ErrorCode.NOT_FOUND, "媒体不存在", 404)
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
        raise AppError(ErrorCode.MEDIA_NOT_READY, "媒体尚未就绪", 404)
    abs_path = filekit.resolve_within_storage(rel)
    if not abs_path:
        raise AppError(ErrorCode.NOT_FOUND, "文件不存在", 404)
    return abs_path, mime
