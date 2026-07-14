"""系统服务：初始化判定与执行。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password, rsa_decrypt, validate_password
from app.models.system_status import SystemStatus
from app.models.users import User
from app.schemas.common import AppError, ErrorCode
from app.schemas.system import InitIn


def is_initialized(db: Session) -> bool:
    status = db.query(SystemStatus).filter(SystemStatus.id == 1).first()
    return status.initialized if status else False


def init_system(db: Session, data: InitIn) -> User:
    """首次初始化：创建 admin 用户，标记系统已初始化。"""
    status = db.query(SystemStatus).filter(SystemStatus.id == 1).first()
    if status and status.initialized:
        raise AppError(ErrorCode.ALREADY_INITIALIZED, "系统已初始化", 409)

    try:
        plain_password = rsa_decrypt(_get_private_pem(db), data.password)
    except ValueError:
        raise AppError(ErrorCode.RSA_DECRYPT_FAILED, "密码解密失败", 400) from None

    pw_errors = validate_password(plain_password)
    if pw_errors:
        raise AppError(ErrorCode.PASSWORD_TOO_WEAK, "密码强度不足", 400, {"errors": pw_errors})

    email = data.email.lower().strip()
    password_hash = hash_password(plain_password)

    user = User(
        email=email,
        password_hash=password_hash,
        nickname=data.nickname,
        role="admin",
        status="active",
    )
    db.add(user)
    db.flush()

    if status:
        status.initialized = True
        status.admin_user_id = user.id
    else:
        status = SystemStatus(id=1, initialized=True, admin_user_id=user.id)
        db.add(status)

    db.commit()
    db.refresh(user)
    return user


def _get_private_pem(db: Session) -> str:
    from app.services.rsa_service import get_or_create_rsa_key

    key = get_or_create_rsa_key(db)
    return key.private_key_pem
