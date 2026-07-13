"""应用配置。

从环境变量 / `.env` 文件读取。首次启动若 `.env` 不存在则从 `.env.example`
复制；若 `JWT_SECRET` 为空则自动生成并写回 `.env`。
"""

from __future__ import annotations

import os
import secrets
import shutil
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录：backend/ 的父目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"


def _ensure_env_file() -> None:
    """首次启动：`.env` 不存在则从 `.env.example` 复制。

    若 `JWT_SECRET` 为空则自动生成并写回。
    """
    if not ENV_FILE.exists():
        if ENV_EXAMPLE.exists():
            shutil.copy2(ENV_EXAMPLE, ENV_FILE)
        else:  # 极端情况：example 也没有，建一个空文件
            ENV_FILE.touch()

    # 检查 JWT_SECRET
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
        # 限制权限（仅类 Unix）
        try:
            os.chmod(ENV_FILE, 0o600)
        except OSError:
            pass


_ensure_env_file()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    APP_NAME: str = "Moments"
    DEBUG: bool = False
    # 生产环境为 True 时 Cookie Secure=True
    SECURE_COOKIES: bool = False

    # 数据库
    DB_URL: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'app.db').as_posix()}"

    # JWT
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    COOKIE_NAME: str = "moments_token"
    CSRF_COOKIE_NAME: str = "moments_csrf"

    # 邀请链接对外域名
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # 存储
    STORAGE_ROOT: str = str(PROJECT_ROOT / "storage")
    MEDIA_IMAGE_MAX_MB: int = 40
    MEDIA_VIDEO_MAX_MB: int = 200

    # 媒体处理
    THUMB_SIZE: int = 400
    LARGE_SIZE: int = 2160
    WEBP_THUMB_QUALITY: int = 80
    WEBP_LARGE_QUALITY: int = 90

    # 日志
    LOG_DIR: str = str(PROJECT_ROOT / "logs")
    LOG_LEVEL: str = "INFO"

    # 后端宿主
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # 前端 dist 目录（生产模式静态托管）
    FRONTEND_DIST: str = str(PROJECT_ROOT / "frontend" / "dist")


settings = Settings()  # type: ignore[call-arg]


# 规范化为绝对路径（.env 可能给相对值，相对项目根目录解析）
def _abs(p: str) -> str:
    pp = Path(p)
    return str(pp if pp.is_absolute() else (PROJECT_ROOT / pp))


settings.FRONTEND_DIST = _abs(settings.FRONTEND_DIST)
settings.STORAGE_ROOT = _abs(settings.STORAGE_ROOT)
settings.LOG_DIR = _abs(settings.LOG_DIR)
# SQLite 路径相对项目根目录解析
if (
    settings.DB_URL.startswith("sqlite:///")
    and not Path(settings.DB_URL[len("sqlite:///") :]).is_absolute()
):
    settings.DB_URL = f"sqlite:///{PROJECT_ROOT / settings.DB_URL[len('sqlite:///') :]}"


def get_storage_root() -> Path:
    p = Path(settings.STORAGE_ROOT)
    p.mkdir(parents=True, exist_ok=True)
    return p
