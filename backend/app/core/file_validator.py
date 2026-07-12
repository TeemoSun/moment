from __future__ import annotations

import filetype
from PIL import Image

from app.logging_conf import logger


IMAGE_ALLOWED = {"jpg", "jpeg", "png", "webp", "gif"}
VIDEO_ALLOWED = {"mp4", "webm"}
EXECUTABLE_BLOCKED = {
    "exe", "elf", "pe", "dll", "so", "dylib", "com",
    "bat", "sh", "ps1", "vbs", "msi", "scr",
}


class FileValidationError(Exception):
    pass


def detect_format(head: bytes, declared_name: str) -> str | None:
    kind = filetype.guess(head)
    if kind is not None:
        return kind.extension.lower()
    name_lower = declared_name.lower()
    for ext in IMAGE_ALLOWED | VIDEO_ALLOWED:
        if name_lower.endswith(f".{ext}"):
            logger.warning("Falling back to extension match for {}", declared_name)
            return ext
    return None


def validate_upload(
    head: bytes,
    declared_name: str,
    size_bytes: int,
    max_image: int,
    max_video: int,
) -> tuple[str, str]:
    ext = declared_name.rsplit(".", 1)[-1].lower() if "." in declared_name else ""
    if ext in EXECUTABLE_BLOCKED:
        raise FileValidationError(f"Executable/script extension blocked: .{ext}")

    real_ext = detect_format(head, declared_name)
    if real_ext is None:
        raise FileValidationError("Unable to determine real file format")

    if real_ext in IMAGE_ALLOWED:
        media_type = "image"
        if size_bytes > max_image:
            raise FileValidationError(f"Image too large: {size_bytes} > {max_image}")
    elif real_ext in VIDEO_ALLOWED:
        media_type = "video"
        if size_bytes > max_video:
            raise FileValidationError(f"Video too large: {size_bytes} > {max_video}")
    else:
        raise FileValidationError(f"File format not allowed: {real_ext}")

    if ext and ext != real_ext:
        logger.warning(
            "Extension mismatch for {}: declared={}, actual={}",
            declared_name, ext, real_ext,
        )

    return media_type, real_ext


def get_image_dimensions(path: str) -> tuple[int, int]:
    try:
        with Image.open(path) as img:
            return img.size
    except Exception as e:
        logger.error("Failed to read image dimensions: {}", e)
        return 0, 0