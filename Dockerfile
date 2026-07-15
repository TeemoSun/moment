# syntax=docker/dockerfile:1.7
# ===== Stage 1: 前端构建 =====
FROM node:20-bookworm-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ===== Stage 2: 后端依赖（独立缓存段）=====
FROM python:3.12-slim-bookworm AS deps
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ===== Stage 3: runtime =====
FROM python:3.12-slim-bookworm AS runtime
# 安装 ffmpeg（视频首帧抽取），同一层内清理 apt 缓存
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && ln -sf /usr/bin/ffmpeg /usr/local/bin/ffmpeg \
    && ln -sf /usr/bin/ffprobe /usr/local/bin/ffprobe

# 从 deps 段拷贝已装好的 venv 与 uv 二进制
COPY --from=deps /app/backend/.venv /app/backend/.venv
COPY --from=deps /usr/local/bin/uv /usr/local/bin/uv

# 创建非 root 用户
RUN groupadd -r app && useradd -r -g app -d /app -s /usr/sbin/nologin app

WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/backend/.venv/bin:$PATH"

COPY backend/ ./
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

RUN chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/docs', timeout=2)" || exit 1

# alembic 迁移由 main.py lifespan 自动执行，无需在此重复
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "app.main:app"]