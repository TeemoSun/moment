"""FastAPI app 入口。

挂载 API 路由 + 生产模式静态托管前端 dist。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response

from alembic import command
from app.config import BACKEND_ROOT, ENV_FILE, ensure_runtime_env, settings

logger = logging.getLogger("app")


def _run_alembic_upgrade() -> None:
    """运行 alembic upgrade head。"""
    alembic_ini = BACKEND_ROOT / "alembic.ini"
    if not alembic_ini.exists():
        logger.warning("alembic.ini not found at %s, skipping migration", alembic_ini)
        return
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(alembic_cfg, "head")


def _ensure_system_status() -> None:
    """确保 system_status 表存在初始行（幂等，防并发）。"""
    from sqlalchemy import text

    from app.database import SessionLocal

    db = SessionLocal()
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ensure_runtime_env()
    if ENV_FILE.exists():
        import app.config as _cfg

        _cfg.settings = _cfg._create_settings()
    from app.database import ensure_data_dir

    ensure_data_dir()
    from app.logging import setup_logging

    setup_logging()
    _run_alembic_upgrade()
    _ensure_system_status()
    logger.info("Moments backend started")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

if settings.CORS_ORIGINS:
    from fastapi.middleware.cors import CORSMiddleware

    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


def register_routes(app: FastAPI) -> None:
    """注册所有 API 路由。

    在此函数内 include_router 以确保所有 /api/* 路由在 SPA fallback 之前注册。
    示例：
        from app.api.v1 import router as v1_router
        app.include_router(v1_router, prefix="/api/v1")
    """


register_routes(app)


@app.get("/api/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


_frontend_dist = Path(settings.FRONTEND_DIST)
if _frontend_dist.exists() and (_frontend_dist / "index.html").exists():
    from fastapi.staticfiles import StaticFiles

    assets_dir = _frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> Response:
        if full_path.startswith("api/") or full_path == "api":
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)

        index_file = _frontend_dist / "index.html"
        return FileResponse(index_file)
