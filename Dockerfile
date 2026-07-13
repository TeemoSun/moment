# ===== Stage 1: 前端构建 =====
FROM node:20-bookworm-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ===== Stage 2: 后端运行 =====
FROM python:3.12-slim AS runtime
# 安装 ffmpeg（视频首帧抽取）
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
# 先拷依赖描述以便利用缓存
COPY backend/pyproject.toml backend/uv.lock* ./backend/
RUN cd backend && uv sync --frozen --no-dev || uv sync --no-dev

COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# 启动时自动迁移 + gunicorn 运行
CMD ["sh", "-c", "cd backend && uv run alembic upgrade head && uv run gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000 app.main:app"]