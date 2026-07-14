"""文件校验、命名、落盘工具。"""

from __future__ import annotations

import io
import secrets
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

import filetype
from PIL import Image

from app.config import get_storage_root, settings
from app.schemas.common import AppError, ErrorCode

SUPPORTED_IMAGE_FORMATS = {"jpeg", "jpg", "png", "webp", "gif"}
SUPPORTED_VIDEO_FORMATS = {"mp4", "mov", "webm", "avi"}
DANGEROUS_MIMES = {
    "application/x-dosexec",
    "application/x-executable",
    "application/x-msdos-program",
    "application/x-elf",
    "application/x-mach-binary",
}


def detect_kind(content: bytes) -> str:
    """用 filetype.guess 检测，返回 'image' 或 'video'。不支持的抛 400。"""
    kind = filetype.guess(content)
    if kind is None:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "不支持的文件类型", 400)
    if kind.mime in DANGEROUS_MIMES:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "存在危险的文件类型，已被拒绝", 400)
    if kind.mime.startswith("image/"):
        return "image"
    if kind.mime.startswith("video/"):
        return "video"
    raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "不支持的文件类型", 400)


def detect_kind_from_file(path: Path) -> str:
    """与 detect_kind 相同，但从文件路径读取头部检测，避免全量读入内存。"""
    with open(path, "rb") as f:
        header = f.read(261)
    return detect_kind(header)


def validate_image(content: bytes) -> tuple[str, Image.Image]:
    """校验真实图片格式，返回 (format_lower, PIL.Image)。失败抛 400。"""
    kind = filetype.guess(content)
    if kind is None or not kind.mime.startswith("image/"):
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "不是有效的图片文件", 400)
    try:
        Image.open(io.BytesIO(content)).verify()
        img = Image.open(io.BytesIO(content))
    except Exception:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "图片文件无效", 400) from None
    fmt = (img.format or "").lower()
    if fmt not in SUPPORTED_IMAGE_FORMATS:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "不支持的图片格式", 400)
    return fmt, img


def validate_image_file(path: Path) -> str:
    """从文件路径校验真实图片格式，返回 format_lower。避免全量读入内存。"""
    kind = filetype.guess(str(path))
    if kind is None or not kind.mime.startswith("image/"):
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "不是有效的图片文件", 400)
    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            fmt = (img.format or "").lower()
    except Exception:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "图片文件无效", 400) from None
    if fmt not in SUPPORTED_IMAGE_FORMATS:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "不支持的图片格式", 400)
    return fmt


def validate_video(content: bytes) -> str:
    """校验视频真实格式，返回 format_lower。用 filetype + ffprobe。"""
    kind = filetype.guess(content)
    if kind is None or not kind.mime.startswith("video/"):
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "不是有效的视频文件", 400)
    ext = kind.extension.lower()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-of", "json", tmp_path],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "无法解析视频文件", 400)
    except subprocess.TimeoutExpired:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "视频校验超时", 400) from None
    finally:
        if tmp_path is not None:
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass
    if ext not in SUPPORTED_VIDEO_FORMATS:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "不支持的视频格式", 400)
    return ext


def validate_video_file(path: Path) -> str:
    """从文件路径校验视频真实格式，返回 format_lower。避免全量读入内存。"""
    kind = filetype.guess(str(path))
    if kind is None or not kind.mime.startswith("video/"):
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "不是有效的视频文件", 400)
    ext = kind.extension.lower()
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "无法解析视频文件", 400)
    if ext not in SUPPORTED_VIDEO_FORMATS:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "不支持的视频格式", 400)
    return ext


def stream_to_file(file_obj, dest: Path, max_bytes: int) -> int:
    """分块流式写入文件，返回字节数。超限抛 FILE_TOO_LARGE。"""
    total = 0
    chunk_size = 1024 * 1024  # 1MB
    file_obj.seek(0)
    with open(dest, "wb") as f:
        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                f.close()
                try:
                    dest.unlink()
                except OSError:
                    pass
                raise AppError(ErrorCode.FILE_TOO_LARGE, "文件过大", 413)
            f.write(chunk)
    return total


def check_size(kind: str, size: int) -> None:
    """kind in image/video。超限抛 AppError FILE_TOO_LARGE 413。"""
    if kind == "image":
        max_bytes = settings.MEDIA_IMAGE_MAX_MB * 1024 * 1024
    elif kind == "video":
        max_bytes = settings.MEDIA_VIDEO_MAX_MB * 1024 * 1024
    else:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "未知的媒体类型", 400)
    if size > max_bytes:
        raise AppError(ErrorCode.FILE_TOO_LARGE, "文件过大", 413)


def generate_filename(ext: str) -> str:
    """时间戳_6位UUID.ext。token_hex(3) = 6 hex chars。"""
    return f"{int(time.time())}_{secrets.token_hex(3)}.{ext}"


def get_media_dir() -> Path:
    """storage/media/YYYY-MM/，自动创建。"""
    d = get_storage_root() / "media" / datetime.now().strftime("%Y-%m")
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_avatars_dir() -> Path:
    """storage/avatars/，自动创建。"""
    d = get_storage_root() / "avatars"
    d.mkdir(parents=True, exist_ok=True)
    return d


def safe_save_bytes(directory: Path, filename: str, content: bytes) -> Path:
    """落盘。若目标已存在则重新生成 filename 直到不冲突。返回绝对路径。"""
    target = directory / filename
    if not target.exists():
        target.write_bytes(content)
        return target
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    while target.exists():
        filename = generate_filename(ext)
        target = directory / filename
    target.write_bytes(content)
    return target


def resolve_within_storage(rel_path: str) -> Path | None:
    """解析相对路径，校验仍在 STORAGE_ROOT 内（防穿越）。返回绝对路径或 None。"""
    root = get_storage_root().resolve()
    p = (root / rel_path).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return None
    return p if p.is_file() else None
