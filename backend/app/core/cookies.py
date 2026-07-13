"""Cookie 设置/清除 + CSRF double-submit。"""

from __future__ import annotations

import secrets

from fastapi import Response

from app.config import settings


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(response: Response, token: str, csrf_token: str) -> None:
    """JWT HttpOnly + CSRF 非HttpOnly, SameSite=Lax, Secure=settings.SECURE_COOKIES."""
    max_age = settings.JWT_EXPIRE_DAYS * 86400
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.SECURE_COOKIES,
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=settings.SECURE_COOKIES,
        max_age=max_age,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """两个 cookie 都设为空 + max_age=0 删除。"""
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value="",
        httponly=True,
        samesite="lax",
        secure=settings.SECURE_COOKIES,
        max_age=0,
        path="/",
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value="",
        httponly=False,
        samesite="lax",
        secure=settings.SECURE_COOKIES,
        max_age=0,
        path="/",
    )
