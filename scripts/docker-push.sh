#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/teemosun/moment}"
DATE_TAG="$(date +%Y%m%d)"

echo "==> [1/3] 构建 Docker 镜像: ${IMAGE_NAME}:latest 与 ${IMAGE_NAME}:${DATE_TAG}"
docker build \
  -t "${IMAGE_NAME}:latest" \
  -t "${IMAGE_NAME}:${DATE_TAG}" \
  .

echo "==> [2/3] 推送镜像到 GHCR"
docker push "${IMAGE_NAME}:latest"
docker push "${IMAGE_NAME}:${DATE_TAG}"

echo "==> [3/3] 完成: 已成功推送 ${IMAGE_NAME}:latest 与 ${IMAGE_NAME}:${DATE_TAG}"
