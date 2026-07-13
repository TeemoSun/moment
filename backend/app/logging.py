"""日志配置：RotatingFileHandler 写 logs/backend.log，同时输出到 stderr。"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "backend.log"

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    # 文件
    fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # 控制台
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    _configured = True
