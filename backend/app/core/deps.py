"""依赖注入：get_current_user / require_admin / verify_csrf。"""

from __future__ import annotations

from fastapi import Cookie, Depends, Request
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.jwt import decode_token
from app.database import get_db
from app.models.users import User
from app.schemas.common import AppError, ErrorCode


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=settings.COOKIE_NAME),
) -> User:
    """从 cookie 读 JWT -> decode -> 查 user。"""
    if not token:
        raise AppError(ErrorCode.AUTH_REQUIRED, "需要登录", 401)

    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except ExpiredSignatureError:
        raise AppError(ErrorCode.AUTH_REQUIRED, "登录已过期，请重新登录", 401) from None
    except (InvalidTokenError, KeyError, ValueError):
        raise AppError(ErrorCode.AUTH_REQUIRED, "登录凭证无效，请重新登录", 401) from None

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppError(ErrorCode.AUTH_REQUIRED, "用户不存在", 401)

    if user.status == "deactivated":
        raise AppError(ErrorCode.ACCOUNT_DEACTIVATED, "账号已注销", 401)

    if user.status == "disabled":
        raise AppError(ErrorCode.ACCOUNT_DISABLED, "账号已被禁用", 403)

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """role != admin -> 403 ADMIN_REQUIRED。"""
    if user.role != "admin":
        raise AppError(ErrorCode.ADMIN_REQUIRED, "需要管理员权限", 403)
    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=settings.COOKIE_NAME),
) -> User | None:
    """可选认证：失败/未登录返回 None，不抛错。用于媒体访问（公开媒体可匿名看）。"""
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (ExpiredSignatureError, InvalidTokenError, KeyError, ValueError):
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    if user.status != "active":
        return None
    return user


def verify_csrf(request: Request) -> None:
    """校验 X-CSRF-Token header == CSRF cookie。"""
    header_token = request.headers.get("X-CSRF-Token")
    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)

    if not header_token or not cookie_token or header_token != cookie_token:
        raise AppError(ErrorCode.CSRF_FAILED, "CSRF 校验失败，请刷新页面重试", 403)
