"""应用配置。

从环境变量 / `.env` 文件读取。首次启动若 `.env` 不存在则从 `.env.example`
复制；若 `JWT_SECRET` 为空则自动生成并写回 `.env`。

注意：本模块 import 时不会写磁盘。需显式调用 `ensure_runtime_env()` 才会
创建/更新 `.env`（含 JWT_SECRET 自动生成）。
"""

from __future__ import annotations

import os
import secrets
import shutil
import sys
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"


def ensure_runtime_env() -> None:
    """确保 `.env` 存在且 `JWT_SECRET` 非空。

    首次调用时：
    - `.env` 不存在则从 `.env.example` 复制（不存在则创建空文件）
    - `JWT_SECRET` 为空则自动生成并写回
    - 设置文件权限 600

    多 worker 安全：使用 fcntl 文件锁（仅 Unix；Windows 跳过锁）。
    进程内仅执行一次。
    """
    if getattr(ensure_runtime_env, "_done", False):
        return

    _ensure_env_file_locked()
    ensure_runtime_env._done = True  # type: ignore[attr-defined]


def _ensure_env_file_locked() -> None:
    lock_fd = None
    try:
        if sys.platform != "win32":
            import fcntl

            lock_path = str(ENV_FILE) + ".lock"
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)

        _ensure_env_file_inner()
    finally:
        if lock_fd is not None:
            import fcntl

            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)


def _ensure_env_file_inner() -> None:
    if not ENV_FILE.exists():
        if ENV_EXAMPLE.exists():
            shutil.copy2(ENV_EXAMPLE, ENV_FILE)
        else:
            ENV_FILE.touch()

    content = ENV_FILE.read_text(encoding="utf-8")
    needs_secret = True
    new_lines: list[str] = []
    found_secret_line = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("JWT_SECRET="):
            found_secret_line = True
            val = stripped[len("JWT_SECRET=") :].strip()
            if val:
                needs_secret = False
                new_lines.append(line)
            else:
                new_lines.append(f"JWT_SECRET={secrets.token_urlsafe(48)}")
        else:
            new_lines.append(line)

    if not found_secret_line:
        new_lines.append(f"JWT_SECRET={secrets.token_urlsafe(48)}")

    new_content = "\n".join(new_lines)
    if not new_content.endswith("\n"):
        new_content += "\n"

    if needs_secret or not found_secret_line:
        ENV_FILE.write_text(new_content, encoding="utf-8")
        try:
            os.chmod(ENV_FILE, 0o600)
        except OSError:
            pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Moments"
    DEBUG: bool = False
    SECURE_COOKIES: bool = False
    RATE_LIMIT_ENABLED: bool = True
    ALLOW_INSECURE_CLIPBOARD: bool = False

    DB_URL: str = ""

    POSTGRES_USER: str = "moments"
    POSTGRES_PASSWORD: str = "moments"
    POSTGRES_DB: str = "moments"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    COOKIE_NAME: str = "moments_token"
    CSRF_COOKIE_NAME: str = "moments_csrf"

    PUBLIC_BASE_URL: str = "http://localhost:8000"

    STORAGE_ROOT: str = str(PROJECT_ROOT / "storage")
    MEDIA_IMAGE_MAX_MB: int = 40
    MEDIA_VIDEO_MAX_MB: int = 200

    THUMB_SIZE: int = 400
    LARGE_SIZE: int = 2160
    WEBP_THUMB_QUALITY: int = 80
    WEBP_LARGE_QUALITY: int = 90

    LOG_DIR: str = str(PROJECT_ROOT / "logs")
    LOG_LEVEL: str = "INFO"

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    FRONTEND_DIST: str = str(PROJECT_ROOT / "frontend" / "dist")

    CORS_ORIGINS: str = ""

    @field_validator("DB_URL", mode="before")
    @classmethod
    def _default_db_url(cls, v: Any) -> Any:
        if not v:
            return "postgresql+psycopg://moments:moments@localhost:5432/moments"
        return v

    @field_validator("STORAGE_ROOT", "LOG_DIR", "FRONTEND_DIST", mode="before")
    @classmethod
    def _abs_path(cls, v: Any) -> Any:
        if not isinstance(v, str) or not v:
            return v
        p = Path(v)
        if p.is_absolute():
            return str(p)
        return str(PROJECT_ROOT / p)


def _create_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = _create_settings()


def get_storage_root() -> Path:
    p = Path(settings.STORAGE_ROOT)
    p.mkdir(parents=True, exist_ok=True)
    return p
