"""Test fixtures.

测试使用 PostgreSQL。所有测试共享一个 ``moments_test`` 库；每个测试开始前通过
TRUNCATE（RESTART IDENTITY CASCADE）清空所有业务表，实现完全隔离。
仅需一个可用的 PG 服务（默认从环境变量读取，复用生产 PG 凭证）。
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

TEST_DB_NAME = "moments_test"


def _base_url() -> str:
    import app.config as cfg

    return (
        f"postgresql+psycopg://{cfg.settings.POSTGRES_USER}:{cfg.settings.POSTGRES_PASSWORD}"
        f"@{cfg.settings.POSTGRES_HOST}:{cfg.settings.POSTGRES_PORT}"
    )


def _test_db_url() -> str:
    return f"{_base_url()}/{TEST_DB_NAME}"


def _ensure_test_db() -> None:
    """确保 moments_test 库存在（首次运行时创建）。"""
    admin_engine = create_engine(f"{_base_url()}/postgres", isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB_NAME}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(autouse=True)
def _override_db_url(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    _ensure_test_db()
    test_url = _test_db_url()

    monkeypatch.setenv("DB_URL", test_url)
    monkeypatch.setenv("SKIP_ALEMBIC", "1")
    monkeypatch.setenv("STORAGE_ROOT", "/tmp/moment_test_storage")

    import app.config as cfg

    cfg.settings = cfg._create_settings()

    from app import database

    database.engine = create_engine(test_url, echo=False, future=True, pool_pre_ping=True)
    database.SessionLocal = sessionmaker(
        bind=database.engine, autoflush=False, autocommit=False, future=True
    )

    import app.models  # noqa: F401 - ensure all models registered
    from app.database import Base

    Base.metadata.create_all(bind=database.engine)

    # 每个测试前清空所有业务表（保留 alembic_version），重置自增序列
    db = database.SessionLocal()
    try:
        db.execute(
            text(
                "TRUNCATE TABLE rsa_keys, system_status, users, file_metadata, "
                "friendships, invite_codes, likes, posts, comments, post_media, "
                "bots, bot_reply_logs RESTART IDENTITY CASCADE"
            )
        )
        db.commit()
        # system_status 种子行
        db.execute(
            text(
                "INSERT INTO system_status "
                "(id, initialized, admin_user_id, created_at, updated_at) "
                "SELECT 1, false, NULL, now(), now() "
                "WHERE NOT EXISTS (SELECT 1 FROM system_status)"
            )
        )
        db.commit()
    finally:
        db.close()

    try:
        yield
    finally:
        database.engine.dispose()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    from app.main import app

    with TestClient(app) as c:
        yield c
