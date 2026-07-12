from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "production"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8443
    APP_URL: str = "https://localhost:8443"

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/db/moment.sqlite3"

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MEDIA_TOKEN_EXPIRE_MINUTES: int = 10

    # Initial admin (auto-seeded on first startup, admin should change password after login)
    INIT_ADMIN_PASSWORD: str = "admin123456"
    INIT_ADMIN_INVITE_CODE: str = "WELCOME01"

    MAX_IMAGE_SIZE_MB: int = 50
    MAX_VIDEO_SIZE_MB: int = 200
    UPLOAD_DIR: str = "./data/uploads"

    MAX_COMMENT_DEPTH: int = 10

    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "3/hour"
    RATE_LIMIT_UPLOAD: str = "20/hour"

    LOG_DIR: str = "./data/logs"
    LOG_LEVEL: str = "INFO"

    SSL_CERT_FILE: str = ""
    SSL_KEY_FILE: str = ""

    @field_validator("JWT_SECRET")
    @classmethod
    def _secret_required(cls, v: str) -> str:
        if not v or len(v) < 16:
            raise ValueError("JWT_SECRET must be set and at least 16 chars")
        return v

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def max_image_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024

    @property
    def max_video_bytes(self) -> int:
        return self.MAX_VIDEO_SIZE_MB * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()

    @property
    def log_path(self) -> Path:
        p = Path(self.LOG_DIR)
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()

    @property
    def ssl_paths(self) -> tuple[Path, Path]:
        if self.SSL_CERT_FILE and self.SSL_KEY_FILE:
            return Path(self.SSL_CERT_FILE), Path(self.SSL_KEY_FILE)
        return PROJECT_ROOT / "data/ssl/cert.pem", PROJECT_ROOT / "data/ssl/key.pem"

    @property
    def db_path_dir(self) -> Path:
        return PROJECT_ROOT / "data/db"

    @property
    def db_url(self) -> str:
        if self.DATABASE_URL.startswith("sqlite"):
            import re
            return re.sub(
                r"sqlite\+aiosqlite:///[^?]+",
                f"sqlite+aiosqlite:///{self.db_path_dir / 'moment.sqlite3'}",
                self.DATABASE_URL,
            )
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]