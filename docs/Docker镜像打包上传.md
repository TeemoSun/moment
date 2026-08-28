# Docker 镜像打包与上传流程

本项目通过根目录 `Dockerfile`（多阶段构建）打包镜像并上传到 Docker Hub，便于部署机器直接 `docker pull`。

## 前置条件

1. 本机已安装 Docker。
2. 已在 Docker Hub 注册账号，并在本机执行过 `docker login`（凭证存于 `~/.docker/config.json`）。
3. 当前工作目录为仓库根目录（含 `Dockerfile`、`frontend/`、`backend/`）。
4. 已安装 `git`，且仓库有提交记录（用于生成 commit tag）。

## Dockerfile 说明

`Dockerfile` 采用三阶段多阶段构建（Multi-Stage Build）：

- **Stage 1 `frontend-builder`**：基于 `node:20-alpine`，利用 npm 淘宝镜像源与 BuildKit 缓存挂载执行 `npm ci` + `npm run build`，产出 `frontend/dist`。
- **Stage 2 `backend-builder`**：基于 `python:3.12-slim`，使用 `uv`（阿里云 PyPI 源）并配合 BuildKit 缓存挂载执行 `uv sync --frozen --no-dev`，在容器内预编译 Python 字节码并生成纯净的 `.venv` 虚拟环境。
- **Stage 3 `runtime`**：基于 `python:3.12-slim`，从静态镜像引入独立的 `ffmpeg` 与 `ffprobe`（避免安装 200+ 个无用 X11/Mesa 系统图形库，体积减少数百兆且无需漫长网络下载）；仅从前置阶段复制 `.venv` 与前端 `dist`，拷入后端代码，不残留 `uv` 工具与 wheel 缓存；暴露 `8000` 端口，直接通过虚拟环境中的 `gunicorn` + `uvicorn` worker 启动。

> 注意：alembic 迁移由 `app.main.lifespan` 在容器启动时自动执行，Dockerfile 不单独运行迁移。

## tag 命名规范

每次构建同时打两个 tag：

- `<user>/moments:latest` —— 始终指向最新构建，便于部署机器稳定拉取。
- `<user>/moments:<date>` —— 形如 `20260715`（YYYYMMDD），按发布日期归档，便于回滚定位。

其中 `<user>` 为 Docker Hub 用户名（本项目使用 `pigzho`）。

> **同日多次发布**：若同一天内多次构建发布，日期 tag 会被覆盖（`docker push` 同名 tag 会更新该 tag 指向的新 digest）。这是预期行为——日期 tag 始终代表当日最新构建。如需保留历史版本快照，可在日期后追加 `-v2`、`-v3` 等后缀（如 `20260715-v2`）。

## 打包与上传步骤

以下命令在仓库根目录执行。将 `<user>` 替换为实际 Docker Hub 用户名。

### 1. 构建镜像

```bash
docker build -t <user>/moments:latest -t <user>/moments:$(date +%Y%m%d) .
```

- 构建会走前端 `npm run build` + 后端 `uv sync` 全流程，首次较慢，后续命中 Docker 缓存。
- 同时打 `latest` 与当日日期 tag。

### 2. 登录 Docker Hub（如未登录）

```bash
docker login
```

输出 `Login Succeeded` 即可。已登录可跳过。

### 3. 推送镜像

```bash
docker push <user>/moments:latest
docker push <user>/moments:$(date +%Y%m%d)
```

推送完成后，部署机器 `docker pull <user>/moments:latest` 即可拉取。

## 删除 tag

### 删除本地 tag

```bash
docker rmi <user>/moments:<tag>
```

### 删除远程 tag（Docker Hub）

Docker CLI 不支持删除远程 tag，需通过 Docker Hub API：

```bash
# 从 ~/.docker/config.json 读取登录凭证换取 JWT
USERPASS=$(python3 -c 'import json; d=json.load(open("/home/teemo/.docker/config.json")); print(d["auths"]["https://index.docker.io/v1/"]["auth"])' | base64 -d)
USER=$(echo "$USERPASS" | cut -d: -f1)
PASS=$(echo "$USERPASS" | cut -d: -f2-)
TOKEN=$(curl -s "https://hub.docker.com/v2/users/login/" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')

# 删除指定 tag（HTTP 204 表示成功）
curl -s -o /dev/null -w "%{http_code}\n" \
  -X DELETE "https://hub.docker.com/v2/repositories/<user>/moments/tags/<tag>/" \
  -H "Authorization: JWT $TOKEN"
```

将 `<user>` 与 `<tag>` 替换为实际值。删除远程 tag 不影响镜像 digest，仅在 Docker Hub 界面移除该标签引用。

## 部署机切换为拉取远程镜像

默认 `docker-compose.yml` 使用 `build: .` 本地构建。若部署机希望直接拉取已推送的远程镜像，将 `moments` 服务段改为：

```yaml
  moments:
    image: <user>/moments:latest
    # 删除 build: .
```

随后 `docker compose pull && docker compose up -d` 即可。

## 一键脚本参考

可将以下内容保存为 `scripts/docker-push.sh`（需 `chmod +x`）：

```bash
#!/usr/bin/env bash
set -euo pipefail

USER="${DOCKER_USER:-pigzho}"
DATE_TAG="$(date +%Y%m%d)"

echo "==> Building <user>/moments:latest and :$DATE_TAG"
docker build -t "$USER/moments:latest" -t "$USER/moments:$DATE_TAG" .

echo "==> Pushing tags"
docker push "$USER/moments:latest"
docker push "$USER/moments:$DATE_TAG"

echo "==> Done: $USER/moments:latest, $USER/moments:$DATE_TAG"
```

用法：`DOCKER_USER=pigzho bash scripts/docker-push.sh`。