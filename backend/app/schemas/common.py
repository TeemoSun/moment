"""统一错误响应模型与异常类。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorOut(BaseModel):
    code: str
    message: str
    detail: dict[str, Any] = {}


class ErrorCode:
    AUTH_REQUIRED = "AUTH_REQUIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    ADMIN_REQUIRED = "ADMIN_REQUIRED"
    CSRF_FAILED = "CSRF_FAILED"
    NOT_INITIALIZED_NEEDED = "NOT_INITIALIZED_NEEDED"
    ALREADY_INITIALIZED = "ALREADY_INITIALIZED"
    RSA_DECRYPT_FAILED = "RSA_DECRYPT_FAILED"
    INVALID_INVITE = "INVALID_INVITE"
    EMAIL_EXISTS = "EMAIL_EXISTS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    PASSWORD_TOO_WEAK = "PASSWORD_TOO_WEAK"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_MEDIA = "UNSUPPORTED_MEDIA"
    MEDIA_NOT_READY = "MEDIA_NOT_READY"
    MEDIA_NOT_OWNED = "MEDIA_NOT_OWNED"
    MEDIA_ALREADY_USED = "MEDIA_ALREADY_USED"
    INVALID_CURSOR = "INVALID_CURSOR"
    DUPLICATE_LIKE = "DUPLICATE_LIKE"
    ALREADY_LIKED = "ALREADY_LIKED"
    NOT_LIKED = "NOT_LIKED"
    COMMENT_NOT_FOUND = "COMMENT_NOT_FOUND"
    EMPTY_COMMENT = "EMPTY_COMMENT"
    FRIEND_REQUEST_EXISTS = "FRIEND_REQUEST_EXISTS"
    ALREADY_FRIENDS = "ALREADY_FRIENDS"
    CANNOT_FRIEND_SELF = "CANNOT_FRIEND_SELF"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    FRIEND_REQUEST_NOT_FOUND = "FRIEND_REQUEST_NOT_FOUND"
    NOT_FRIENDS = "NOT_FRIENDS"
    INTERNAL = "INTERNAL"


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)
