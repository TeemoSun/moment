#!/usr/bin/env bash
# 一键编译前端并产出 dist
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[build] 编译前端..."
(
  cd "$ROOT/frontend"
  if [ ! -d node_modules ]; then
    echo "[build] 安装依赖 npm ci..."
    npm ci || npm install
  fi
  npm run build
)

DIST="$ROOT/frontend/dist"
if [ -d "$DIST" ]; then
  echo "[build] 前端构建完成：$DIST"
  ls -la "$DIST"
else
  echo "[build] 错误：未找到 $DIST" >&2
  exit 1
fi