"""认证服务：注册、登录（含锁定）、刷新、登出。"""

from __future__ import annotations

from datetime import timedelta

from fastapi import Response
from sqlalchemy.orm import Session

from app.core.cookies import clear_auth_cookies, generate_csrf_token, set_auth_cookies
from app.core.jwt import create_access_token
from app.core.security import hash_password, rsa_decrypt, validate_password, verify_password
from app.models.invite_codes import InviteCode
from app.models.users import User
from app.schemas.auth import LoginIn, RegisterIn
from app.schemas.common import AppError, ErrorCode
from app.utils.time import utcnow


def register(db: Session, data: RegisterIn) -> User:
    """注册新用户（需有效邀请码）。"""
    email = data.email.lower().strip()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise AppError(ErrorCode.EMAIL_EXISTS, "Email already registered", 409)

    invite = db.query(InviteCode).filter(InviteCode.code == data.invite_code).first()
    if not invite or invite.status != "active" or invite.used_by_id is not None:
        raise AppError(ErrorCode.INVALID_INVITE, "Invalid invite code", 400)
    if invite.expires_at and invite.expires_at <= utcnow():
        raise AppError(ErrorCode.INVALID_INVITE, "Invalid invite code", 400)

    try:
        from app.services.rsa_service import get_or_create_rsa_key

        key = get_or_create_rsa_key(db)
        plain_password = rsa_decrypt(key.private_key_pem, data.password)
    except ValueError:
        raise AppError(ErrorCode.RSA_DECRYPT_FAILED, "Failed to decrypt password", 400) from None

    pw_errors = validate_password(plain_password)
    if pw_errors:
        raise AppError(ErrorCode.PASSWORD_TOO_WEAK, "Password too weak", 400, {"errors": pw_errors})

    password_hash = hash_password(plain_password)
    user = User(
        email=email,
        password_hash=password_hash,
        nickname=data.nickname,
        role="user",
        status="active",
    )
    db.add(user)
    db.flush()

    invite.status = "used"
    invite.used_by_id = user.id
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, data: LoginIn, response: Response) -> User:
    """登录（含锁定逻辑）。"""
    email = data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise AppError(ErrorCode.INVALID_CREDENTIALS, "Invalid credentials", 401)

    if user.status == "disabled":
        raise AppError(ErrorCode.ACCOUNT_DISABLED, "Account disabled", 403)

    if user.status == "deactivated":
        raise AppError(ErrorCode.ACCOUNT_DEACTIVATED, "Account deactivated", 403)

    now = utcnow()
    if user.locked_until:
        locked_until = user.locked_until
        if locked_until > now:
            retry_after = int((locked_until - now).total_seconds())
            raise AppError(
                ErrorCode.ACCOUNT_LOCKED,
                "Account locked",
                403,
                {"locked_until": locked_until.isoformat(), "retry_after_seconds": retry_after},
            )

    try:
        from app.services.rsa_service import get_or_create_rsa_key

        key = get_or_create_rsa_key(db)
        plain_password = rsa_decrypt(key.private_key_pem, data.password)
    except ValueError:
        _increment_failed(db, user)
        raise AppError(ErrorCode.INVALID_CREDENTIALS, "Invalid credentials", 401) from None

    if not verify_password(plain_password, user.password_hash):
        _increment_failed(db, user)
        raise AppError(ErrorCode.INVALID_CREDENTIALS, "Invalid credentials", 401)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()

    token = create_access_token(user.id, user.role)
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, token, csrf_token)
    return user


def _increment_failed(db: Session, user: User) -> None:
    user.failed_login_count += 1
    if user.failed_login_count >= 5:
        user.locked_until = utcnow() + timedelta(minutes=15)
        db.commit()
        raise AppError(
            ErrorCode.ACCOUNT_LOCKED,
            "Account locked",
            403,
            {"locked_until": user.locked_until.isoformat(), "retry_after_seconds": 900},
        )
    db.commit()


def refresh(db: Session, current_user: User, response: Response) -> User:
    """续签：重新签 JWT 写 cookie，返回 user。"""
    token = create_access_token(current_user.id, current_user.role)
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, token, csrf_token)
    return current_user


def logout(response: Response) -> None:
    clear_auth_cookies(response)
