FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS backend-build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --no-dev --frozen
COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist ./app/static

FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libwebp-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=backend-build /app/backend /app/backend

ENV APP_ENV=production
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8443
ENV DATABASE_URL=sqlite+aiosqlite:///./data/db/moment.sqlite3
ENV UPLOAD_DIR=./data/uploads
ENV LOG_DIR=./data/logs

VOLUME ["/app/data"]

EXPOSE 8443

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8443", \
     "--ssl-certfile", "/app/data/ssl/cert.pem", "--ssl-keyfile", "/app/data/ssl/key.pem"]