#!/usr/bin/env bash
# 同时启动前后端开发服务器，Ctrl+C 一起退出
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PIDS=()

cleanup() {
  echo ""
  echo "[dev] 正在关闭所有服务..."
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
  echo "[dev] 已全部退出"
}
trap cleanup SIGINT SIGTERM EXIT

# ===== 读取 .env 配置 =====
BACKEND_HOST="0.0.0.0"
BACKEND_PORT="8000"
if [ -f "$ROOT/.env" ]; then
  while IFS='=' read -r key value; do
    key="$(echo "$key" | xargs)"
    value="$(echo "$value" | xargs)"
    case "$key" in
      BACKEND_HOST) BACKEND_HOST="$value" ;;
      BACKEND_PORT) BACKEND_PORT="$value" ;;
    esac
  done < <(grep -v '^#' "$ROOT/.env" | grep -v '^$')
fi

export VITE_BACKEND_PORT="$BACKEND_PORT"

# ===== 后端 =====
echo "[dev] 安装后端依赖..."
echo "[dev] 启动后端 Go 服务 on ${BACKEND_HOST}:${BACKEND_PORT}..."
(
  cd "$ROOT/backend"
  if command -v uv >/dev/null 2>&1; then
    uv sync --extra dev
  fi
)

echo "[dev] 启动后端 uvicorn (reload) on ${BACKEND_HOST}:${BACKEND_PORT}..."
(
  cd "$ROOT/backend"
  if command -v uv >/dev/null 2>&1; then
    uv run uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
  else
    python -m uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
  fi
  go run ./cmd/moments
) &
PIDS+=($!)

# ===== 前端 =====
echo "[dev] 启动前端 Vite dev server..."
(
  cd "$ROOT/frontend"
  if [ ! -d node_modules ]; then
    echo "[dev] 前端未安装依赖，执行 npm install..."
    npm install
  fi
  npm run dev -- --host 0.0.0.0
) &
PIDS+=($!)

echo "[dev] 后端: http://0.0.0.0:${BACKEND_PORT}  | 前端: http://0.0.0.0:5173"
echo "[dev] 按 Ctrl+C 退出全部"

wait -n
EXIT_CODE=$?
echo "[dev] 子进程退出 (code=$EXIT_CODE)，正在关闭..."
exit $EXIT_CODE
