"""Test fixtures."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(autouse=True)
def _override_db_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DB_URL", db_url)
    monkeypatch.setenv("SKIP_ALEMBIC", "1")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))

    import app.config as cfg

    cfg.settings = cfg._create_settings()

    from app import database

    database.engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
        future=True,
    )

    @event.listens_for(database.engine, "connect")
    def _set_pragma(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    database.SessionLocal = sessionmaker(
        bind=database.engine, autoflush=False, autocommit=False, future=True
    )

    import app.models  # noqa: F401 - ensure all models registered
    from app.database import Base

    Base.metadata.create_all(bind=database.engine)

    db = database.SessionLocal()
    try:
        db.execute(
            text(
                "INSERT INTO system_status "
                "(id, initialized, admin_user_id, created_at, updated_at) "
                "SELECT 1, 0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
                "WHERE NOT EXISTS (SELECT 1 FROM system_status)"
            )
        )
        db.commit()
    finally:
        db.close()


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
