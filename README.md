# Moments

> 朋友圈风格的小型社交应用。设计方案见 `docs/`。

## 技术栈

- **后端**：Python 3.12 + FastAPI + SQLAlchemy 2.x + uv
- **后端**：Go 1.23 + Chi + pgx/v5 (纯静态编译 CGO_ENABLED=0)
- **前端**：React 18 + TypeScript + Vite + Zustand + animal-island-ui（npm 包）
- **数据库**：PostgreSQL 16
- **部署**：Docker（多阶段构建，镜像发布在 GHCR `ghcr.io/teemosun/moment`）

## 快速开始

### 开发模式（前后端并行）

```bash
bash scripts/dev.sh
```

- 后端：http://localhost:8000 （API 在 `/api`）
- 前端：http://localhost:5173 （Vite dev server，自动代理 `/api` 到后端）
- 按 `Ctrl+C` 一起退出

### 生产构建

```bash
bash scripts/build.sh        # 构建前端 dist
cd backend && uv sync        # 安装后端依赖
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
bash scripts/build.sh                                                    # 构建前端 dist
cd backend && CGO_ENABLED=0 go build -ldflags="-s -w" -o moments ./cmd/moments # 编译后端二进制
./moments                                                                # 启动服务
```

构建后由后端托管 `frontend/dist`，访问 http://localhost:8000 即可。

### Docker 部署

本仓库提供 `docker-compose.yml`，用一条命令拉起 PostgreSQL 16 + 应用，适合服务器一键部署。镜像由 GitHub Actions 自动构建并发布到 GHCR（`ghcr.io/teemosun/moment`），无需本地构建。

#### 1. 准备配置

在部署目录放入以下两个文件（可直接从仓库复制后修改）：

- `docker-compose.yml`（仓库根目录）
- `.env`（从 `.env.example` 复制）

```bash
cp docker-compose.yml .env.example .env
```

按需修改 `.env`：

| 变量 | 说明 | 建议 |
|------|------|------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | 数据库凭证（compose 启动 PG 时使用，应用也用它连接） | 生产请改强密码 |
| `JWT_SECRET` | 留空即可，首次启动自动生成并写回 `.env`（权限 600） | — |
| `SECURE_COOKIES` | 生产（HTTPS）设为 `true` | `true` |
| `PUBLIC_BASE_URL` | 对外访问域名，影响邀请链接生成 | 改为实际域名，如 `https://moments.example.com` |
| `CORS_ORIGINS` | 跨域白名单，逗号分隔；同站部署留空即可 | — |
| `LLM_API_KEY` / `LLM_MODEL` | AI 机器人功能，不需要可留空 | — |

#### 2. 拉起服务

```bash
docker compose up -d
```

- `postgres:16` 作为 `db` 服务启动，`moments` 应用等待 `db` 健康后启动。
- 应用启动时**自动执行 Alembic 迁移**，无需手动建表。
- 应用托管前端构建产物，访问 http://localhost:8000 即可。

#### 3. 使用远程镜像（推荐）

`docker-compose.yml` 默认 `build: .`（本地构建）。若要直接拉取已发布的远程镜像，编辑 `moments` 服务段，把：

```yaml
  moments:
    build: .
```

改为：

```yaml
  moments:
    image: ghcr.io/teemosun/moment:latest
```

随后：

```bash
docker compose pull      # 拉取最新镜像
docker compose up -d
```

#### 4. 常用运维命令

```bash
docker compose logs -f moments   # 查看应用日志
docker compose logs -f db        # 查看数据库日志
docker compose restart moments   # 仅重启应用
docker compose down               # 停止并移除容器（数据卷保留）
docker compose up -d              # 再次拉起
```

#### 5. 持久化与数据位置

- `./data/pg` — PostgreSQL 数据（挂载到容器 `/var/lib/postgresql/data`）
- `./storage` — 用户上传媒体（挂载到容器 `/app/storage`）
- `./logs` — 运行时日志
- `.env` 也以只读挂载进应用容器（`/app/.env`）

> `docker compose down` 不会删除上述目录的数据；如需彻底清空请手动删除 `data/`、`storage/`、`logs/`。

#### 6. 升级镜像

```bash
docker compose pull
docker compose up -d
```

应用容器会以新镜像重建，数据库容器保持不变，数据不丢失。迁移会在启动时自动执行。

#### 7. 镜像打包与上传

若需自行构建并推送镜像（如修改代码后发布），流程见 `docs/Docker镜像打包上传.md`。

## 首次启动

- `.env` 不存在时自动从 `.env.example` 复制
- `JWT_SECRET` 为空时自动生成并写回 `.env`（权限 600）

## Git Hooks（可选，推荐）

启用 pre-commit 钩子（前端 ESLint+Prettier、后端 Ruff+Mypy）：

```bash
git config core.hooksPath .githooks
```

## 目录结构

```
moments/
├── backend/      后端（FastAPI）
├── backend/      后端（Go 1.23 + Chi + pgx）
├── frontend/     前端（Vite + React）
├── docs/         设计与实现文档
├── scripts/      dev.sh / build.sh
├── storage/      媒体文件存储（运行时生成）
├── data/         SQLite 数据库（运行时生成）
├── data/         PostgreSQL 数据（运行时生成）
├── logs/         运行时日志
├── Dockerfile
└── docker-compose.yml
```

详见 `docs/项目实现方案.md`。