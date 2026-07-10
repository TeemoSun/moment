from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.rate_limit import limiter
from app.core.validators import validate_email, validate_username
from app.database import get_db
from app.deps import get_current_user
from app.models import InviteCode, User
from app.schemas import (
    InviteCodeOut, LoginIn, MessageOut, RefreshOut, RegisterIn, TokenOut, UserOut,
)
from app.security import (
    create_access_token, create_refresh_token, decode_refresh_token,
    hash_password, verify_password,
)

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/api/auth/refresh"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        secure=not settings.is_dev,
        samesite="strict",
        path=REFRESH_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)


def _avatar_url(user: User) -> str | None:
    return f"/api/media/avatar/{user.id}" if user.avatar_media_id else None


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id, username=user.username, display_name=user.display_name,
        bio=user.bio, avatar_url=_avatar_url(user), created_at=user.created_at,
    )


@router.post("/register", response_model=TokenOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(
    request: Request,
    body: RegisterIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    if not validate_username(body.username):
        raise HTTPException(400, "Invalid username (3-32 alphanumeric/underscore)")
    if not validate_email(body.email):
        raise HTTPException(400, "Invalid email")

    invite = await db.execute(
        select(InviteCode).where(InviteCode.code == body.invite_code)
    )
    invite_code = invite.scalar_one_or_none()
    if invite_code is None:
        raise HTTPException(400, "Invalid invite code")
    if invite_code.used_count >= invite_code.max_uses:
        raise HTTPException(400, "Invite code exhausted")
    if invite_code.expires_at and invite_code.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(400, "Invite code expired")

    exists = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(409, "Username or email already taken")

    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        is_admin=False,
    )
    db.add(user)
    await db.flush()

    invite_code.used_count += 1
    if invite_code.used_count >= invite_code.max_uses:
        invite_code.used_by = user.id

    access = create_access_token(user.id, user.is_admin)
    refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh)
    return TokenOut(access_token=access, token_type="bearer", user=_user_out(user))


@router.post("/login", response_model=TokenOut)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    body: LoginIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.username == body.username)
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")

    access = create_access_token(user.id, user.is_admin)
    refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh)
    return TokenOut(access_token=access, token_type="bearer", user=_user_out(user))


@router.post("/refresh", response_model=RefreshOut)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(401, "No refresh token")
    payload = decode_refresh_token(token)
    if payload is None:
        raise HTTPException(401, "Invalid refresh token")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(401, "User not found")

    new_access = create_access_token(user.id, user.is_admin)
    return RefreshOut(access_token=new_access, token_type="bearer")


@router.post("/logout", response_model=MessageOut)
async def logout(response: Response):
    _clear_refresh_cookie(response)
    return MessageOut(message="Logged out")


def generate_invite_code() -> str:
    return secrets.token_urlsafe(16)[:24]