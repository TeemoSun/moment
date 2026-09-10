# syntax=docker/dockerfile:1

# ===== Stage 1: 前端构建 =====
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com \
    && npm ci
COPY frontend/ ./
RUN npm run build

# ===== Stage 2: 后端 Go 静态编译 =====
FROM golang:1.23-alpine AS backend-builder
WORKDIR /app/backend
ARG GOPROXY=https://goproxy.cn,direct
ENV GOPROXY=${GOPROXY} \
    CGO_ENABLED=0 \
    GOOS=linux

COPY backend/go.mod backend/go.sum ./
RUN go mod download

COPY backend/ ./
RUN go build -ldflags="-s -w" -o /moments ./cmd/moments

# ===== Stage 3: 生产运行时 =====
FROM alpine:3.20 AS runtime

RUN apk --no-cache add ca-certificates tzdata ffmpeg

WORKDIR /app

COPY --from=backend-builder /moments /app/moments
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist
COPY backend/assets /app/backend/assets

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/app/moments", "-healthcheck"]

ENTRYPOINT ["/app/moments"]