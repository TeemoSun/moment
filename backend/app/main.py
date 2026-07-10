from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import get_settings
from app.core.rate_limit import limiter
from app.database import init_db
from app.logging_conf import logger, setup_logging
from app.routers import admin, auth, comments, friends, media, posts, users
from app.ssl_gen import ensure_self_signed_cert

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting Moment (env={})", settings.APP_ENV)
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.log_path.mkdir(parents=True, exist_ok=True)
    cert, key = settings.ssl_paths
    if not (settings.SSL_CERT_FILE and settings.SSL_KEY_FILE):
        ensure_self_signed_cert(cert, key)
    await init_db()
    logger.info("Database initialized")
    from app.database import AsyncSessionLocal
    from app.services.seed_service import ensure_initial_admin
    await ensure_initial_admin(AsyncSessionLocal)
    yield
    logger.info("Shutting down")


def _serve_with_encoding(request: Request, path: Path) -> FileResponse:
    accept_encoding = request.headers.get("accept-encoding", "")
    for algo, ext in (("br", ".br"), ("gzip", ".gz")):
        if algo in accept_encoding:
            precompressed = path.with_name(path.name + ext)
            if precompressed.exists():
                return FileResponse(
                    precompressed,
                    headers={
                        "Content-Encoding": algo,
                        "Cache-Control": "public, max-age=86400",
                    },
                )
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


def create_app() -> FastAPI:
    app = FastAPI(
        title="Moment",
        docs_url="/api/docs" if settings.is_dev else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.is_dev else None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.middleware("http")
    async def csp_and_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if settings.is_dev:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data: blob:; "
                "media-src 'self' blob:; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; "
                "connect-src 'self';"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data: blob:; "
                "media-src 'self' blob:; "
                "style-src 'self'; "
                "script-src 'self'; "
                "connect-src 'self';"
            )
        return response

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(friends.router)
    app.include_router(media.router)
    app.include_router(posts.router)
    app.include_router(comments.router)
    app.include_router(admin.router)

    static_dir = Path(__file__).parent / "static"
    index_file = static_dir / "index.html"

    if static_dir.exists() and index_file.exists():
        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str, request: Request):
            if full_path.startswith("api"):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            candidate = static_dir / full_path
            if full_path and candidate.is_file():
                return _serve_with_encoding(request, candidate)
            return _serve_with_encoding(request, index_file)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.error("Unhandled error on {}: {}", request.url.path, exc)
        if settings.is_dev:
            return JSONResponse(
                status_code=500,
                content={"detail": str(exc)},
            )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )

    return app


app = create_app()