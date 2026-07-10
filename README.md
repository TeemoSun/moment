# Moment

一个面向小范围用户的「朋友圈」式社交 Web 应用。用户可发布图文/视频动态，好友可查看、评论（链式回复）、点赞。

## 技术栈

- **后端**：FastAPI + SQLAlchemy 2.0 (async) + SQLite (可切 Postgres)
- **前端**：Vite + React + TypeScript + TanStack Query + TailwindCSS
- **认证**：JWT 访问令牌 + 刷新令牌 (httpOnly cookie)
- **密码哈希**：argon2
- **图片处理**：Pillow（缩略图生成）
- **压缩**：Brotli + Gzip（前端预压缩）
- **依赖管理**：uv (Python) / npm (前端)
- **HTTPS**：自签证书自动生成

## 快速开始

### 快速运行

```bash
# 一键启动（自动创建 .env、生成 JWT_SECRET、构建前端、启动 HTTPS 服务）
bash scripts/start.sh
```

服务启动后访问 `https://localhost:8443`。

### 初始管理员

首次启动会自动创建管理员账号和邀请码（无需手动操作）：

- **用户名**：`admin`
- **初始密码**：`admin123456`（可在 `.env` 中通过 `INIT_ADMIN_PASSWORD` 自定义）
- **邀请码**：`WELCOME01`（可在 `.env` 中通过 `INIT_ADMIN_INVITE_CODE` 自定义）

登录后请立即在「设置 - 修改密码」中修改初始密码。

用邀请码 `WELCOME01` 即可注册新用户。

### 日常启动

```bash
bash scripts/start.sh
```

Ctrl+C 终止所有服务。

### 单独构建前端

```bash
bash scripts/build.sh
```

### 开发模式（前后端分离热更新）

```bash
# 终端1：后端
cd backend && JWT_SECRET=dev-secret uv run uvicorn app.main:app --reload --port 18443

# 终端2：前端（代理 /api 到后端）
cd frontend && npm run dev
```

## 项目结构

```
moment/
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 应用工厂
│   │   ├── config.py        # 配置
│   │   ├── database.py      # DB 引擎
│   │   ├── models/          # ORM 模型
│   │   ├── routers/         # API 路由
│   │   ├── services/        # 业务逻辑
│   │   ├── core/            # 工具（文件校验、缩略图、限流、权限）
│   │   └── static/          # 前端构建产物（gitignore）
│   └── pyproject.toml
├── frontend/         # React 前端
├── scripts/           # 启动/构建脚本
├── data/              # 数据目录（Docker 卷映射）
│   ├── db/            # SQLite 数据库
│   ├── uploads/       # 上传文件 + 缩略图
│   ├── logs/          # 日志
│   └── ssl/           # 自签证书
├── docs/DESIGN.md     # 设计文档
├── Dockerfile
└── .env.example
```

## 安全特性

- **认证**：JWT 短效访问令牌 + httpOnly 刷新 cookie，邀请码注册
- **密码**：argon2 哈希
- **文件上传**：magic bytes 真实格式校验，禁可执行文件，大小限制
- **XSS**：React 自动转义 + CSP 头
- **CSRF**：SameSite=Strict cookie + Bearer 授权
- **限流**：登录/注册/上传接口限流
- **SPA 路由安全**：`/api/*` 严格 404，不回退 index.html
- **HTTPS**：自签证书自动生成

## Docker 部署

```bash
docker build -t moment .
docker run -d -p 8443:8443 -v ./data:/app/data \
  -e JWT_SECRET=$(openssl rand -hex 32) \
  moment
```

## 数据库切换

默认 SQLite，切换 Postgres 只需修改 `.env`：

```ini
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/moment
```

## 配置项

见 `.env.example`。