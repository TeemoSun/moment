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
  # 杀掉子进程组
  wait 2>/dev/null || true
  echo "[dev] 已全部退出"
}
trap cleanup SIGINT SIGTERM EXIT

# ===== 后端 =====
echo "[dev] 启动后端 uvicorn (reload)..."
(
  cd "$ROOT/backend"
  if command -v uv >/dev/null 2>&1; then
    uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  else
    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  fi
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
  npm run dev
) &
PIDS+=($!)

echo "[dev] 后端: http://localhost:8000  | 前端: http://localhost:5173"
echo "[dev] 按 Ctrl+C 退出全部"

wait