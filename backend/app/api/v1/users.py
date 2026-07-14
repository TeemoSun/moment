"""用户路由：个人资料、头像、改密、注销、查看他人、头像访问。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import BACKEND_ROOT, get_storage_root
from app.core.deps import get_current_user, verify_csrf
from app.database import get_db
from app.models.users import User
from app.schemas.user import AvatarOut, MeOut, MeUpdateIn, OtherUserOut, PasswordChangeIn
from app.services import user_service

router = APIRouter()


@router.get("/me", response_model=MeOut)
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return user_service.get_me(db, current_user)


@router.patch("/me", response_model=MeOut)
def update_me(
    data: MeUpdateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    user = user_service.update_me(db, current_user, data)
    return user_service.get_me(db, user)


@router.post("/me/password")
def change_password(
    data: PasswordChangeIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> Response:
    user_service.change_password(db, current_user, data)
    return Response(status_code=204)


@router.post("/me/avatar", response_model=AvatarOut)
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    user = user_service.upload_avatar(db, current_user, file)
    return {"avatar_url": user_service.avatar_url_for(user)}


@router.post("/me/deactivate")
def deactivate(
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> Response:
    user_service.deactivate(db, current_user)
    return Response(status_code=204)


@router.get("/users/{user_id}", response_model=OtherUserOut)
def get_other_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return user_service.get_other_user(db, current_user.id, user_id)


@router.get("/avatars/default")
def get_default_avatar() -> FileResponse:
    default_path = BACKEND_ROOT / "assets" / "default_avatar.png"
    return FileResponse(default_path, media_type="image/png")


@router.get("/avatars/{user_id}")
def get_user_avatar(user_id: int, db: Session = Depends(get_db)) -> FileResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.avatar_path:
        default_path = BACKEND_ROOT / "assets" / "default_avatar.png"
        return FileResponse(default_path, media_type="image/png")

    storage_root = get_storage_root()
    file_path = (storage_root / user.avatar_path).resolve()
    storage_root_resolved = storage_root.resolve()

    if not str(file_path).startswith(str(storage_root_resolved)):
        default_path = BACKEND_ROOT / "assets" / "default_avatar.png"
        return FileResponse(default_path, media_type="image/png")

    if not file_path.is_file():
        default_path = BACKEND_ROOT / "assets" / "default_avatar.png"
        return FileResponse(default_path, media_type="image/png")

    return FileResponse(file_path, media_type="image/webp")
