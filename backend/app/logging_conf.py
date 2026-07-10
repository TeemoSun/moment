from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from app.config import get_settings

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    log_dir = settings.log_path
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    log_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | "
        "{name}:{function}:{line} | {message}"
    )
    log_level = settings.LOG_LEVEL.upper()

    logger.add(
        sys.stderr,
        level=log_level,
        format=log_format,
        colorize=True,
    )
    logger.add(
        log_dir / "app.log",
        level=log_level,
        format=log_format,
        rotation="10 MB",
        retention=5,
        compression="zip",
        encoding="utf-8",
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        log_dir / "access.log",
        level="INFO",
        format=log_format,
        rotation="10 MB",
        retention=3,
        compression="zip",
        encoding="utf-8",
        filter=lambda record: record["extra"].get("access") is True,
    )
    _configured = True


logger = logger