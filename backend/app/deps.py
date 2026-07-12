from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.security import decode_access_token, decode_media_token

settings = get_settings()


CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

MEDIA_COOKIE = "media_token"


async def _resolve_user(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise CREDENTIALS_ERROR
    token = auth.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    if payload is None:
        raise CREDENTIALS_ERROR
    user_id = payload.get("sub")
    if not user_id:
        raise CREDENTIALS_ERROR
    user = await _resolve_user(db, user_id)
    if user is None:
        raise CREDENTIALS_ERROR
    return user


async def get_current_user_for_media(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Auth dependency for media endpoints.

    Accepts either the Bearer access token (for API calls) or the
    ``media_token`` cookie (for browser-native <img>/<video> requests that
    cannot send custom headers).
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ").strip()
        payload = decode_access_token(token)
        if payload is not None:
            user_id = payload.get("sub")
            if user_id:
                user = await _resolve_user(db, user_id)
                if user is not None:
                    return user

    cookie_token = request.cookies.get(MEDIA_COOKIE)
    if cookie_token:
        payload = decode_media_token(cookie_token)
        if payload is not None:
            user_id = payload.get("sub")
            if user_id:
                user = await _resolve_user(db, user_id)
                if user is not None:
                    return user

    raise CREDENTIALS_ERROR


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"