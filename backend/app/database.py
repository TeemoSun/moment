"""数据库引擎、会话工厂与 Base。"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine: Engine = create_engine(
    settings.DB_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
    future=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection: sqlite3.Connection, connection_record) -> None:  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_data_dir() -> None:
    if settings.DB_URL.startswith("sqlite:///"):
        db_path_str = settings.DB_URL[len("sqlite:///") :]
        db_path = Path(db_path_str)
        db_path.parent.mkdir(parents=True, exist_ok=True)
