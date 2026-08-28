# syntax=docker/dockerfile:1

# ===== Stage 1: 前端构建 =====
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com \
    && npm ci
COPY frontend/ ./
RUN npm run build

# ===== Stage 2: 后端依赖构建 =====
FROM python:3.12-slim AS backend-builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/backend
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple

COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ===== Stage 3: 生产运行时 =====
FROM python:3.12-slim AS runtime

# 从静态镜像引入独立的 ffmpeg 与 ffprobe（避免安装 200+ 个无用 X11/Mesa 系统库，减少数百兆体积并秒级构建）
COPY --from=mwader/static-ffmpeg:latest /ffmpeg /ffprobe /usr/local/bin/

WORKDIR /app/backend

# 复制已构建好的 Python 虚拟环境与前端静态产物
COPY --from=backend-builder /app/backend/.venv /app/backend/.venv
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# 复制后端业务代码
COPY backend/ ./

# 环境变量配置
ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONPATH="/app/backend" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# alembic 迁移由 main.py lifespan 自动执行；直接使用虚拟环境中的 gunicorn 启动
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "app.main:app"]