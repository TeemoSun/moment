from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageSequence

from app.logging_conf import logger

SMALL_EDGE = 480
MEDIUM_EDGE = 1280
THUMB_QUALITY_SMALL = 80
THUMB_QUALITY_MEDIUM = 85


def _resize_cover(img: Image.Image, max_edge: int) -> Image.Image:
    w, h = img.size
    if max(w, h) <= max_edge:
        return img
    ratio = max_edge / max(w, h)
    new_size = (int(w * ratio), int(h * ratio))
    return img.resize(new_size, Image.LANCZOS)


def generate_image_thumbnails(
    src_path: str | Path, thumb_dir: str | Path, base_name: str
) -> tuple[str | None, str | None]:
    thumb_dir = Path(thumb_dir)
    thumb_dir.mkdir(parents=True, exist_ok=True)
    small_path: str | None = None
    medium_path: str | None = None

    try:
        with Image.open(src_path) as img:
            frames = ImageSequence.Iterator(img)
            first = next(frames).convert("RGB")
            small = _resize_cover(first, SMALL_EDGE)
            small_target = thumb_dir / f"{base_name}_small.webp"
            small.save(small_target, "WEBP", quality=THUMB_QUALITY_SMALL)
            small_path = str(small_target)

            medium = _resize_cover(first, MEDIUM_EDGE)
            medium_target = thumb_dir / f"{base_name}_medium.webp"
            medium.save(medium_target, "WEBP", quality=THUMB_QUALITY_MEDIUM)
            medium_path = str(medium_target)
    except Exception as e:
        logger.error("Thumbnail generation failed for {}: {}", src_path, e)

    return small_path, medium_path


def generate_video_thumbnail(
    src_path: str | Path, thumb_dir: str | Path, base_name: str
) -> str | None:
    try:
        import subprocess

        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src_path),
                "-ss", "00:00:01", "-frames:v", "1",
                "-f", "image2", "-",
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0 or not result.stdout:
            return None
        thumb_dir = Path(thumb_dir)
        thumb_dir.mkdir(parents=True, exist_ok=True)
        target = thumb_dir / f"{base_name}_small.webp"
        with Image.open(BytesIO(result.stdout)) as img:
            small = _resize_cover(img.convert("RGB"), SMALL_EDGE)
            small.save(target, "WEBP", quality=THUMB_QUALITY_SMALL)
        return str(target)
    except Exception as e:
        logger.warning("Video thumbnail skipped (ffmpeg unavailable?): {}", e)
        return None


def get_video_duration(src_path: str | Path) -> float | None:
    try:
        import subprocess
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(src_path),
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning("Video duration probe skipped: {}", e)
    return None