"""FastAPI app 入口。

挂载 API 路由 + 生产模式静态托管前端 dist。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging import setup_logging

setup_logging()

app = FastAPI(title=settings.APP_NAME, docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.get("/api/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


# 生产模式：托管前端 dist
_frontend_dist = Path(settings.FRONTEND_DIST)
if _frontend_dist.exists() and (_frontend_dist / "index.html").exists():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    # 静态资源
    assets_dir = _frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str = "") -> FileResponse:
        # API 路径不走这里（已匹配），其余回退到 index.html
        index_file = _frontend_dist / "index.html"
        return FileResponse(index_file)