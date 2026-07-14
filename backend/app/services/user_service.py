"""用户服务：个人资料、头像、改密、注销。"""

from __future__ import annotations

import io
import secrets
import time

from fastapi import UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from app.config import get_storage_root, settings
from app.core.security import hash_password, rsa_decrypt, validate_password, verify_password
from app.models.file_metadata import FileMetadata
from app.models.users import User
from app.schemas.common import AppError, ErrorCode
from app.schemas.user import MeOut, MeUpdateIn, OtherUserOut, PasswordChangeIn


def avatar_url_for(user: User) -> str:
    if user.avatar_path:
        return f"/api/v1/avatars/{user.id}"
    return "/api/v1/avatars/default"


def user_to_me_out(user: User) -> dict:
    return MeOut(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        signature=user.signature,
        avatar_url=avatar_url_for(user),
        role=user.role,
        status=user.status,
        can_invite=user.can_invite,
        created_at=user.created_at,
    ).model_dump(mode="json")


def get_me(db: Session, user: User) -> dict:
    return user_to_me_out(user)


def update_me(db: Session, user: User, data: MeUpdateIn) -> User:
    if data.nickname is not None:
        user.nickname = data.nickname
    if data.signature is not None:
        user.signature = data.signature
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, data: PasswordChangeIn) -> None:
    from app.services.rsa_service import get_or_create_rsa_key

    key = get_or_create_rsa_key(db)

    try:
        old_plain = rsa_decrypt(key.private_key_pem, data.old_password)
    except ValueError:
        raise AppError(
            ErrorCode.RSA_DECRYPT_FAILED, "Failed to decrypt old password", 400
        ) from None

    if not verify_password(old_plain, user.password_hash):
        raise AppError(ErrorCode.INVALID_CREDENTIALS, "Invalid old password", 400)

    try:
        new_plain = rsa_decrypt(key.private_key_pem, data.new_password)
    except ValueError:
        raise AppError(
            ErrorCode.RSA_DECRYPT_FAILED, "Failed to decrypt new password", 400
        ) from None

    pw_errors = validate_password(new_plain)
    if pw_errors:
        raise AppError(ErrorCode.PASSWORD_TOO_WEAK, "Password too weak", 400, {"errors": pw_errors})

    user.password_hash = hash_password(new_plain)
    db.commit()


def upload_avatar(db: Session, user: User, file: UploadFile) -> User:
    """上传头像：校验 -> 缩略图 -> 存 file_metadata。"""
    if not file.filename:
        raise AppError(ErrorCode.VALIDATION_ERROR, "No file provided", 400)

    file.file.seek(0)
    content = file.file.read()
    max_size = settings.MEDIA_IMAGE_MAX_MB * 1024 * 1024
    if len(content) > max_size:
        raise AppError(ErrorCode.FILE_TOO_LARGE, "File too large", 413)

    try:
        Image.open(io.BytesIO(content)).verify()
        img = Image.open(io.BytesIO(content))
    except Exception:
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "Invalid image file", 400) from None

    fmt = (img.format or "").lower()
    if fmt not in ("jpeg", "jpg", "png", "webp", "gif"):
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA, "Unsupported image format", 400)

    storage_root = get_storage_root()
    avatars_dir = storage_root / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    ts = int(time.time())
    rand = secrets.token_hex(2)
    thumb_name = f"{user.id}_{ts}_{rand}_thumb.webp"
    thumb_path = avatars_dir / thumb_name

    img.thumbnail((settings.THUMB_SIZE, settings.THUMB_SIZE))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")  # type: ignore[assignment]
    img.save(thumb_path, format="WEBP", quality=settings.WEBP_THUMB_QUALITY)

    rel_path = f"avatars/{thumb_name}"
    user.avatar_path = rel_path

    meta = FileMetadata(
        storage_path=rel_path,
        original_name=file.filename or "avatar",
        filename=thumb_name,
        size=thumb_path.stat().st_size,
        mime="image/webp",
        format="webp",
        kind="avatar",
        owner_id=user.id,
    )
    db.add(meta)
    db.commit()
    db.refresh(user)
    return user


def deactivate(db: Session, user: User) -> None:
    user.status = "deactivated"
    db.commit()


def get_other_user(db: Session, viewer_id: int, user_id: int) -> dict:
    from app.services.friend_service import get_friendship_status

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppError(ErrorCode.NOT_FOUND, "User not found", 404)

    is_deactivated = user.status == "deactivated"
    avatar_url = "/api/v1/avatars/default" if is_deactivated else avatar_url_for(user)
    friendship_status = get_friendship_status(db, viewer_id, user_id)

    return OtherUserOut(
        id=user.id,
        nickname=user.nickname,
        signature=user.signature,
        avatar_url=avatar_url,
        is_deactivated=is_deactivated,
        created_at=user.created_at,
        friendship_status=friendship_status,
    ).model_dump(mode="json")
