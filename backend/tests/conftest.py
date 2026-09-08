"""Test fixtures.

测试使用 PostgreSQL。所有测试共享一个 ``moments_test`` 库；每个测试开始前通过
TRUNCATE（RESTART IDENTITY CASCADE）清空所有业务表，实现完全隔离。整个测试
会话结束后自动 DROP 该测试库并释放相关资源。

仅需一个可用的 PG 服务（默认从环境变量读取，复用生产 PG 凭证）。
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

TEST_DB_NAME = "moments_test"

# 业务表清单，用于每个测试前的 TRUNCATE
_BUSINESS_TABLES = (
    "rsa_keys, system_status, users, file_metadata, "
    "friendships, invite_codes, likes, posts, comments, post_media, "
    "bots, bot_reply_logs"
)


def _base_url() -> str:
    import app.config as cfg

    return (
        f"postgresql+psycopg://{cfg.settings.POSTGRES_USER}:{cfg.settings.POSTGRES_PASSWORD}"
        f"@{cfg.settings.POSTGRES_HOST}:{cfg.settings.POSTGRES_PORT}"
    )


def _test_db_url() -> str:
    return f"{_base_url()}/{TEST_DB_NAME}"


def _create_test_db() -> None:
    """创建 moments_test 库（幂等）。"""
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


def _drop_test_db() -> None:
    """DROP moments_test 库（测试会话结束时调用）。"""
    admin_engine = create_engine(f"{_base_url()}/postgres", isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
    except Exception:
        # 某些 PG 版本不支持 WITH (FORCE)，回退到普通 DROP
        with admin_engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def _session_test_db() -> Generator[None, None, None]:
    """会话级：创建测试库，会话结束后 DROP 它。"""
    _create_test_db()
    try:
        yield
    finally:
        _drop_test_db()


@pytest.fixture(autouse=True)
def _override_db_url(
    _session_test_db: None, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    test_url = _test_db_url()

    monkeypatch.setenv("DB_URL", test_url)
    monkeypatch.setenv("SKIP_ALEMBIC", "1")
    monkeypatch.setenv("STORAGE_ROOT", "/tmp/moment_test_storage")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

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
        db.execute(text(f"TRUNCATE TABLE {_BUSINESS_TABLES} RESTART IDENTITY CASCADE"))
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
