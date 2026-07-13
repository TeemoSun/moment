# Moments

> 朋友圈风格的小型社交应用。设计方案见 `docs/`。

## 技术栈

- **后端**：Python 3.12 + FastAPI + SQLAlchemy 2.x + uv
- **前端**：React 18 + TypeScript + Vite + Zustand + animal-island-ui (CDN)
- **数据库**：SQLite（可切 PostgreSQL）
- **部署**：Docker（多阶段构建）

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
```

构建后由后端托管 `frontend/dist`，访问 http://localhost:8000 即可。

### Docker 部署

```bash
docker build -t moments .
docker-compose up -d
# 访问 http://localhost:8000
```

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
├── frontend/     前端（Vite + React）
├── docs/         设计与实现文档
├── scripts/      dev.sh / build.sh
├── storage/      媒体文件存储（运行时生成）
├── data/         SQLite 数据库（运行时生成）
├── logs/         运行时日志
├── Dockerfile
└── docker-compose.yml
```

详见 `docs/项目实现方案.md`。