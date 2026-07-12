from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
TOKEN_TYPE_MEDIA = "media"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _create_token(
    subject: str,
    token_type: Literal["access", "refresh", "media"],
    extra: dict | None = None,
    expire: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    if expire is None:
        if token_type == TOKEN_TYPE_ACCESS:
            expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        elif token_type == TOKEN_TYPE_MEDIA:
            expire = timedelta(minutes=settings.MEDIA_TOKEN_EXPIRE_MINUTES)
        else:
            expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    exp = now + expire
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, is_admin: bool = False) -> str:
    return _create_token(
        user_id, TOKEN_TYPE_ACCESS, {"admin": is_admin}
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, TOKEN_TYPE_REFRESH)


def create_media_token(user_id: str) -> str:
    return _create_token(user_id, TOKEN_TYPE_MEDIA)


def decode_token(token: str, expected_type: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


def decode_access_token(token: str) -> dict | None:
    return decode_token(token, TOKEN_TYPE_ACCESS)


def decode_refresh_token(token: str) -> dict | None:
    return decode_token(token, TOKEN_TYPE_REFRESH)


def decode_media_token(token: str) -> dict | None:
    return decode_token(token, TOKEN_TYPE_MEDIA)