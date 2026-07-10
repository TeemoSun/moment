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

### 首次运行

```bash
# 1. 复制环境变量配置
cp .env.example .env

# 2. 生成 JWT_SECRET
echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env

# 3. 一键启动（自动安装依赖、构建前端、生成证书、启动 HTTPS 服务）
bash scripts/start.sh
```

服务启动后访问 `https://localhost:8443`。

### 创建管理员与邀请码

首次使用需手动创建管理员账号（需有邀请码才能注册）：

```bash
cd backend
uv run python -c "
import asyncio
from app.database import AsyncSessionLocal, init_db
from app.models import User, InviteCode
from app.security import hash_password

async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        u = User(username='admin', email='admin@example.com',
                 password_hash=hash_password('your-password'), is_admin=True)
        db.add(u); await db.flush()
        c = InviteCode(code='WELCOME01', created_by=u.id, max_uses=100)
        db.add(c); await db.commit()
        print('Done: admin / WELCOME01')

asyncio.run(seed())
"
```

然后用 `WELCOME01` 邀请码注册新用户。

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