from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import Media, User
from app.schemas import MessageOut, PasswordChange, UserBrief, UserOut, UserUpdate
from app.security import hash_password, verify_password
from app.services.media_service import save_user_avatar

router = APIRouter(prefix="/api/users", tags=["users"])


def _avatar_url(user: User) -> str | None:
    return f"/api/media/avatar/{user.id}?v={user.avatar_media_id}" if user.avatar_media_id else None


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id, username=user.username, display_name=user.display_name,
        bio=user.bio, avatar_url=_avatar_url(user), created_at=user.created_at,
    )


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.bio is not None:
        user.bio = body.bio
    await db.flush()
    return _user_out(user)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    media = await save_user_avatar(file, user, db)
    user.avatar_media_id = media.id
    await db.flush()
    return _user_out(user)


@router.post("/me/password", response_model=MessageOut)
async def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "旧密码错误")
    if body.old_password == body.new_password:
        raise HTTPException(400, "新密码不能与旧密码相同")
    user.password_hash = hash_password(body.new_password)
    await db.flush()
    return MessageOut(message="密码修改成功")


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(404, "User not found")
    return _user_out(target)


@router.get("/by-username/{username}", response_model=UserOut)
async def get_user_by_username(
    username: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(404, "User not found")
    return _user_out(target)