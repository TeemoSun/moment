"""后台媒体处理：图片缩略图/大图、视频首帧。"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from PIL import Image

from app.config import get_storage_root, settings
from app.models.file_metadata import FileMetadata
from app.models.post_media import PostMedia

logger = logging.getLogger("app.media")


def _get_session():
    from app.database import SessionLocal

    return SessionLocal()


def process_image_media(media_id: int) -> None:
    """生成缩略图(400px WebP80) + 大图(2160px WebP90)，更新 DB。"""
    db = _get_session()
    try:
        media = db.query(PostMedia).filter(PostMedia.id == media_id).first()
        if not media:
            logger.warning("media %s not found", media_id)
            return
        storage_root = get_storage_root()
        src = (storage_root / media.file_path).resolve()
        if not src.is_file():
            logger.warning("source file missing: %s", src)
            return
        stem = media.filename.rsplit(".", 1)[0]
        thumb_name = f"{stem}_thumb.webp"
        thumb_rel = str(Path(media.file_path).with_name(thumb_name))
        thumb_abs = (storage_root / thumb_rel).resolve()
        large_name = f"{stem}_large.webp"
        large_rel = str(Path(media.file_path).with_name(large_name))
        large_abs = (storage_root / large_rel).resolve()

        img = Image.open(src)
        img.thumbnail((settings.THUMB_SIZE, settings.THUMB_SIZE))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")  # type: ignore[assignment]
        img.save(thumb_abs, format="WEBP", quality=settings.WEBP_THUMB_QUALITY)

        img2 = Image.open(src)
        img2.thumbnail((settings.LARGE_SIZE, settings.LARGE_SIZE))
        if img2.mode in ("RGBA", "P"):
            img2 = img2.convert("RGB")  # type: ignore[assignment]
        img2.save(large_abs, format="WEBP", quality=settings.WEBP_LARGE_QUALITY)

        media.thumb_path = thumb_rel
        media.large_path = large_rel
        db.commit()

        for kind, rel, abspath in (
            ("thumb", thumb_rel, thumb_abs),
            ("large", large_rel, large_abs),
        ):
            db.add(
                FileMetadata(
                    storage_path=rel,
                    original_name=media.filename,
                    filename=abspath.name,
                    size=abspath.stat().st_size,
                    mime="image/webp",
                    format="webp",
                    kind=kind,
                    owner_id=media.owner_id,
                )
            )
        db.commit()
    except Exception:
        logger.exception("process_image_media %s failed", media_id)
    finally:
        db.close()


def process_video_media(media_id: int) -> None:
    """ffmpeg 取首帧 -> 缩略图 WebP；large_path 留空(None)。"""
    db = _get_session()
    try:
        media = db.query(PostMedia).filter(PostMedia.id == media_id).first()
        if not media:
            return
        storage_root = get_storage_root()
        src = (storage_root / media.file_path).resolve()
        if not src.is_file():
            return
        stem = media.filename.rsplit(".", 1)[0]
        thumb_name = f"{stem}_thumb.webp"
        thumb_rel = str(Path(media.file_path).with_name(thumb_name))
        thumb_abs = (storage_root / thumb_rel).resolve()
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vframes",
            "1",
            "-vf",
            f"scale='min({settings.THUMB_SIZE},iw)':-2",
            str(thumb_abs),
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        if r.returncode != 0:
            logger.error("ffmpeg failed: %s", r.stderr.decode("utf-8", "ignore")[:500])
            return
        if thumb_abs.is_file():
            media.thumb_path = thumb_rel
            db.commit()
            db.add(
                FileMetadata(
                    storage_path=thumb_rel,
                    original_name=media.filename,
                    filename=thumb_abs.name,
                    size=thumb_abs.stat().st_size,
                    mime="image/webp",
                    format="webp",
                    kind="thumb",
                    owner_id=media.owner_id,
                )
            )
            db.commit()
    except Exception:
        logger.exception("process_video_media %s failed", media_id)
    finally:
        db.close()
