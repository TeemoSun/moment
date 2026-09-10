# Docker 镜像打包与上传流程

本项目镜像发布到 **GitHub Container Registry（GHCR）**，由 `.github/workflows/docker-publish.yml` 在 push 到 `main`、打 `v*.*.*` tag 或手动触发（workflow_dispatch）时自动构建并推送。

- 镜像地址：`ghcr.io/teemosun/moment`
- Workflow：Build and Publish Docker Image（Buildx + GHA 缓存，`linux/amd64`）

## 镜像构建说明

根目录 `Dockerfile` 采用三阶段多阶段构建（Multi-Stage Build）：

- **Stage 1 `frontend-builder`**：基于 `node:20-alpine`，利用 npm 淘宝镜像源与 BuildKit 缓存挂载执行 `npm ci` + `npm run build`，产出 `frontend/dist`。
- **Stage 2 `backend-builder`**：基于 `golang:1.23-alpine`，采用纯静态编译（`CGO_ENABLED=0`、`GOOS=linux`）构建出轻量且无 libc 依赖的独立单二进制产物 `/moments`。
- **Stage 3 `runtime`**：基于极简 `alpine:3.20`，安装轻量 `ffmpeg`（用于视频首帧截取与缩略图生成）；仅从前置阶段复制 Go 二进制文件、前端 `dist` 与静态内置资产；暴露 `8000` 端口；通过内置 `-healthcheck` flag 探针进行容器健康检查。

> 注意：数据库表结构与 alembic_version 兼容标记由服务启动时自动幂等执行，Dockerfile 不单独运行迁移。

## tag 命名规范

由 `docker/metadata-action` 自动生成，每次构建同时打多个 tag：

- `latest` —— `main` 分支构建始终指向最新，便于部署机器稳定拉取。
- `<YYYYMMDD>` —— 形如 `20260908`，按发布日期归档，便于回滚定位。
- `sha-<short>` —— 每个提交一个短 SHA tag，精确对应代码版本。
- `vX.Y.Z` —— 推送 `v*.*.*` tag 时额外生成 semver tag。

> **同日多次发布**：日期 tag 会被覆盖（同名 tag 指向新 digest），这是预期行为——日期 tag 始终代表当日最新构建。如需保留历史版本快照，可打 `v*.*.*` 版本 tag 或使用 sha tag。

## 发布步骤

### 常规发布（自动）

推送代码到 `main` 即可，GitHub Actions 自动构建并推送全部 tag：

```bash
git push origin main
```

构建进度见仓库 Actions 页，产物见仓库 Packages 页。

### 手动触发

在 GitHub 仓库页 → Actions → "Build and Publish Docker Image" → Run workflow。

### 发布正式版本

```bash
git tag v1.0.0 && git push origin v1.0.0
```

会额外生成 `ghcr.io/teemosun/moment:1.0.0` tag。

## 本地手动构建与推送（备用）

如需在本地构建推送（需要对本仓库有写权限的 GitHub 账号执行过 `gh auth login` 或已配置 GHCR 的 PAT）：

```bash
bash scripts/docker-push.sh
```

脚本会构建并推送 `latest` 与当日日期 tag 到 GHCR。

## 部署机拉取镜像

`docker-compose.yml` 已默认使用 `image: ghcr.io/teemosun/moment:latest`。由于仓库与镜像包均为公开，拉取无需登录：

```bash
docker compose pull && docker compose up -d
```

## 删除 tag / 管理 package

在 GitHub 仓库页 → Packages → `moment` → Package settings 中管理版本与可见性；或用命令行删除指定版本：

```bash
# 列出包版本（需 read:packages 权限的 token）
gh api --paginate /user/packages/container/moment/versions --jq '.[].metadata.container.tags'

# 删除指定版本（VERSION_ID 换成上一步的 id）
gh api -X DELETE /user/packages/container/moment/versions/VERSION_ID
```
