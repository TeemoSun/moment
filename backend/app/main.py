"""FastAPI app 入口。

挂载 API 路由 + 生产模式静态托管前端 dist。
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from alembic import command
from app.config import BACKEND_ROOT, ENV_FILE, ensure_runtime_env, settings
from app.schemas.common import AppError

logger = logging.getLogger("app")


def _guess_content_type(path: Path) -> str:
    import mimetypes

    ct, _ = mimetypes.guess_type(str(path))
    return ct or "application/octet-stream"


def _run_alembic_upgrade() -> None:
    """运行 alembic upgrade head。"""
    if os.environ.get("SKIP_ALEMBIC"):
        return
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
                "SELECT 1, false, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
                "WHERE NOT EXISTS (SELECT 1 FROM system_status)"
            )
        )
        db.commit()
    finally:
        db.close()


def _warmup_rsa() -> None:
    """启动时预热 RSA 密钥对。"""
    from app.database import SessionLocal
    from app.services.rsa_service import get_or_create_rsa_key

    db = SessionLocal()
    try:
        get_or_create_rsa_key(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ensure_runtime_env()
    if ENV_FILE.exists():
        import app.config as _cfg

        _cfg.settings = _cfg._create_settings()
    from app.logging import setup_logging

    setup_logging()
    _run_alembic_upgrade()
    _ensure_system_status()
    _warmup_rsa()
    logger.info("Moments backend started")
    from app.scheduler import start_scheduler

    start_scheduler()
    try:
        yield
    finally:
        from app.scheduler import stop_scheduler

        stop_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/api/docs" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

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
    """注册所有 API 路由。"""
    from app.api.v1 import router as v1_router

    app.include_router(v1_router, prefix="/api/v1")


register_routes(app)


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    from app.schemas.common import ErrorCode

    return JSONResponse(
        status_code=400,
        content={
            "code": ErrorCode.VALIDATION_ERROR,
            "message": "请求参数校验失败",
            "detail": {"errors": exc.errors()},
        },
    )


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    from app.schemas.common import ErrorCode

    _http_status_msg = {
        400: "请求错误",
        401: "未登录或登录已过期",
        403: "无权访问",
        404: "资源不存在",
        405: "请求方法不被允许",
        409: "资源冲突",
        413: "请求体过大",
        422: "请求参数有误",
        429: "请求过于频繁",
    }
    message = _http_status_msg.get(exc.status_code, f"请求出错（HTTP {exc.status_code}）")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": str(exc.detail) if isinstance(exc.detail, str) else ErrorCode.INTERNAL,
            "message": message,
            "detail": {},
        },
    )


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from app.schemas.common import ErrorCode

    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": ErrorCode.INTERNAL, "message": "服务器内部错误", "detail": {}},
    )


@app.get("/api/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


_frontend_dist = Path(settings.FRONTEND_DIST)
_frontend_dist_resolved = _frontend_dist.resolve()
if _frontend_dist.exists() and (_frontend_dist / "index.html").exists():
    from fastapi.staticfiles import StaticFiles

    assets_dir = _frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(request: Request, full_path: str) -> Response:
    if full_path.startswith("api/") or full_path == "api":
        return JSONResponse({"detail": "资源不存在"}, status_code=404)

    file_path = (_frontend_dist / full_path).resolve()
    if full_path and _frontend_dist_resolved in file_path.parents and file_path.is_file():
        return FileResponse(file_path)

    # 尝试预压缩文件（br/gz），根据 Accept-Encoding 选择
    accept_encoding = request.headers.get("accept-encoding", "")
    for enc, ext in (("br", ".br"), ("gzip", ".gz")):
        if enc in accept_encoding:
            compressed = file_path.with_name(file_path.name + ext)
            if compressed.is_file():
                content_type = _guess_content_type(file_path)
                return FileResponse(
                    compressed,
                    media_type=content_type,
                    headers={
                        "Content-Encoding": enc,
                        "Cache-Control": "public, max-age=31536000, immutable",
                        "Vary": "Accept-Encoding",
                    },
                )

    index_file = _frontend_dist / "index.html"
    return FileResponse(index_file)
