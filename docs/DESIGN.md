# Moment — 朋友圈式 Web 应用设计方案

> 状态：设计阶段 | 更新：2026-07-11

## 1. 项目概述

一个面向小范围用户（亲友圈）的「朋友圈」式社交应用。用户可发布图文/视频动态，好友可查看、评论、点赞。采用 FastAPI 单服务一体化架构，前端构建产物由 FastAPI 托管为静态资源，便于打包为 Docker 镜像部署到公网。

### 核心原则

- **架构规范优先**，用户量小不追求极致性能，但代码分层清晰、可维护。
- **安全优先**：公网部署，认证、越权、上传、注入、限流、路由回退均需防护。
- **数据与代码分离**：所有可变数据（DB、上传文件、日志、证书）集中在 `./data/` 目录，便于 Docker 卷映射。
- **数据库可迁移**：SQLite 起步，ORM 兼容 Postgres/MySQL。

## 2. 技术栈

### 2.1 后端

| 组件 | 选型 | 说明 |
|------|------|------|
| Web 框架 | FastAPI (Uvicorn worker) | 单服务一体化 |
| ORM | SQLAlchemy 2.0 + Alembic | 异步引擎，DB 可切换 |
| 数据库 | SQLite (aiosqlite) → 可切 Postgres/MySQL | 仅用 DB 方言差异 |
| 依赖管理 | uv | 锁文件 `uv.lock` |
| 认证 | JWT (访问令牌) + 刷新令牌 | 访问令牌短效(15min)，刷新令牌 httpOnly cookie(30d) |
| 密码哈希 | argon2 (passlib) | 抗 GPU/ASIC |
| 图像处理 | Pillow | 缩略图生成 |
| 证书 | cryptography（自动生成自签）+ mkcert（本地信任可选） | |
| 限流 | slowapi | 内存计数，单进程够用 |
| 压缩 | Brotli + Gzip（StaticFiles + 中间件） | 前端 build 时预生成 .br/.gz |
| 日志 | 标准 logging + loguru 轮转 | 写 `./data/logs/` |

### 2.2 前端

| 组件 | 选型 |
|------|------|
| 构建 | Vite |
| 语言 | TypeScript |
| 框架 | React 18 |
| 数据请求 | TanStack Query |
| 路由 | React Router v6 |
| UI | TailwindCSS + 轻组件库（如 shadcn/ui 或手写） |
| 状态 | Zustand（用户/会话等轻量全局状态） |
| 富文本/转义 | react 渲染前统一转义；禁止 `dangerouslySetInnerHTML`，不使用富文本 HTML |

## 3. 目录结构

```
moment/
├── data/                       # 所有可变数据（Docker 映射此目录）
│   ├── db/
│   │   └── moment.sqlite3
│   ├── uploads/                # 原始上传文件，按年/月分桶
│   │   └── 2026/07/
│   │       ├── {uuid}.{ext}
│   │       └── thumbs/
│   │           ├── {uuid}_small.webp
│   │           └── {uuid}_medium.webp
│   ├── logs/
│   │   ├── app.log
│   │   └── access.log
│   └── ssl/
│       ├── cert.pem
│       └── key.pem
├── backend/
│   ├── pyproject.toml          # uv 管理
│   ├── uv.lock
│   ├── alembic.ini
│   ├── alembic/                # 迁移脚本
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app 工厂 + 中间件挂载
│   │   ├── config.py           # 配置（env + .env）
│   │   ├── database.py         # 引擎、Session、Base
│   │   ├── deps.py             # 依赖注入（当前用户、DB 会话、限流）
│   │   ├── security.py         # JWT、argon2、密码策略
│   │   ├── logging_conf.py     # 日志配置
│   │   ├── ssl_gen.py          # 自签证书生成
│   │   ├── models/             # ORM 模型
│   │   │   ├── user.py
│   │   │   ├── friendship.py
│   │   │   ├── post.py
│   │   │   ├── media.py
│   │   │   ├── comment.py
│   │   │   └── reaction.py
│   │   ├── schemas/            # Pydantic 入/出参
│   │   ├── routers/            # API 路由（按模块）
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── posts.py
│   │   │   ├── comments.py
│   │   │   ├── friends.py
│   │   │   └── media.py
│   │   ├── services/           # 业务逻辑（router 调 service）
│   │   │   ├── auth_service.py
│   │   │   ├── post_service.py
│   │   │   ├── media_service.py
│   │   │   └── ...
│   │   ├── core/               # 通用工具
│   │   │   ├── file_validator.py   # 真实格式校验
│   │   │   ├── thumbnail.py
│   │   │   ├── permissions.py      # 可见范围、越权校验
│   │   │   └── rate_limit.py
│   │   └── static/             # 前端 build 产物（gitignore）
│   │       ├── index.html
│   │       ├── assets/...
│   │       └── (含 .br/.gz 预压缩文件)
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                # axios/fetch 封装 + TanStack Query hooks
│       ├── components/
│       ├── pages/
│       ├── routes/
│       ├── stores/             # zustand
│       ├── utils/              # sanitize, format 等
│       └── styles/
├── scripts/
│   ├── start.sh                # 一键启动前后端
│   ├── stop.sh
│   └── build.sh                 # 前端 build + 拷贝到 backend/app/static
├── data/                       # (运行时生成)
├── docs/
│   └── DESIGN.md
├── .env.example
├── .gitignore
└── README.md
```

## 4. 数据模型

### 4.1 表设计概览

```
users
  id, username (unique), email (unique), password_hash,
  display_name, avatar_media_id (FK→media), bio,
  is_active, is_admin, created_at, updated_at

invite_codes
  id, code (unique), created_by (FK→users), used_by (FK→users nullable),
  expires_at, max_uses, used_count, created_at

friendships
  id, requester_id (FK→users), addressee_id (FK→users),
  status (pending|accepted|blocked), created_at, accepted_at
  唯一约束: (requester_id, addressee_id)

posts
  id, user_id (FK→users), content (text), visibility (public|friends),
  created_at, updated_at, deleted_at (软删除)

media
  id, post_id (FK→posts nullable, 上传时可能先于 post 创建), user_id (FK→users),
  original_filename, stored_filename (uuid.ext), relative_path,
  mime_type, file_format (magic-detected), size_bytes, width, height, duration,
  media_type (image|video), thumb_small_path, thumb_medium_path,
  created_at

comments
  id, post_id (FK→posts), user_id (FK→users),
  parent_id (FK→comments nullable, 链式回复：指向直接父评论，顶级评论为 NULL),
  root_id (FK→comments nullable, 指向整棵评论树的根评论，顶级评论 root_id = 自身 id),
  reply_to_user_id (FK→users nullable, 被@回复的目标用户，便于展示「回复 @xx」),
  depth (顶级=0，逐层 +1，软上限防止无限嵌套，见 4.3),
  content, created_at, deleted_at
  索引: (post_id, root_id, created_at) 楼树聚合查询; (parent_id) 子列表; (user_id) 用户评论历史

reactions
  id, post_id (FK→posts nullable), comment_id (FK→comments nullable), user_id (FK→users),
  type (like|...), created_at
  唯一约束: (user_id, post_id, type) / (user_id, comment_id, type)
```

### 4.2 链式评论设计

采用 **邻接表 + root_id 物化路径** 混合模型，支持任意深度嵌套，同时保证查询高效：

- **`parent_id`**：指向直接父评论（邻接表），用于构建父子关系与单层展开。
- **`root_id`**：指向整棵评论树的根评论（物化根）。所有同一楼的评论共享 `root_id`，可一次性按楼聚合拉取，避免递归查询。
- **`reply_to_user_id`**：被回复目标用户，用于展示「回复 @某人」，与 `parent_id` 解耦——可在同一楼内回复楼内任意一条，而不必逐层嵌套展示。
- **`depth`**：评论层级深度（顶级=0）。设软上限（默认 `MAX_COMMENT_DEPTH=10`），超过则不再允许嵌套，引导用户开新楼或平铺回复，防止无限递归与过深缩进。

#### 存储约定

- 创建顶级评论：`parent_id=NULL`，`root_id=自身id`，`depth=0`，`reply_to_user_id=posts.user_id`（默认回复动态作者）。
- 创建子回复：`parent_id=父评论id`，`root_id=父评论.root_id`，`depth=父评论.depth+1`（校验 < MAX_COMMENT_DEPTH），`reply_to_user_id=被回复者`。
- 事务内写入：先 INSERT 得到 `id`，若为顶级则 UPDATE `root_id=id`；子回复则直接取父评论的 `root_id`。

#### 查询策略

- **列表（按楼聚合）**：`WHERE post_id=? ORDER BY root_id, created_at`，单次查询拿到全部楼 + 楼内所有回复，在应用层按 `root_id` 分组、按 `parent_id` 组装树。
- **懒加载子回复**：信息流/详情先只返回每楼前 N 条 + 子回复总数，点击「展开更多」时 `WHERE parent_id=?` 分页拉取。
- **删除**：软删除（`deleted_at` 置位），保留树结构，展示「该评论已删除」占位；物理删除时校验无子评论，否则仅软删。

#### 越权校验

- 删除评论：仅评论作者本人或被评论动态的作者可删（`comment.user_id == current_user.id` 或 `post.user_id == current_user.id`）。
- 发布评论：需对动态有可见权（`can_view_post`），否则 403。
- `depth` 超限返回 400，引导平铺回复。

### 4.3 可见范围逻辑

- `public`：任何登录用户可见。
- `friends`：仅作者本人 + 双向好友关系（`friendships.status='accepted'`）可见。
- 查询动态时通过 `permissions.py` 的 `can_view_post(user, post)` 统一校验，避免各处手写条件导致越权。

## 5. 认证与授权

### 5.1 流程

1. 注册：提交 `邀请码 + 用户名 + 密码`，服务端校验邀请码有效且未超用，argon2 哈希存储。
2. 登录：`POST /api/auth/login` 返回 `{access_token}`，同时 `Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict; Path=/api/auth`。
3. 受保护接口：`Authorization: Bearer <access_token>`，过期则前端调 `/api/auth/refresh`，用 cookie 里的 refresh_token 换新的 access_token。
4. 登出：`POST /api/auth/logout` 清除 refresh cookie（服务端可维护令牌 jti 黑名单，或直接依赖短期访问令牌自然过期）。

### 5.2 令牌

- 访问令牌：JWT，`exp=15min`，含 `sub(user_id)`、`jti`、`is_admin`。存内存/localStorage，XSS 风险通过内容转义 + CSP 缓解。
- 刷新令牌：JWT，`exp=30d`，`type=refresh`，存 httpOnly cookie，前端 JS 不可读。
- 密钥：`JWT_SECRET` 从环境变量读取，缺失则启动报错（不降级到弱默认）。

### 5.3 鉴权中间件/依赖

- `get_current_user`：解析 Bearer，验签、查黑名单、加载用户。
- `require_admin`：叠加检查 `is_admin`。
- 资源所有权校验：操作帖子/评论/媒体前校验 `obj.user_id == current_user.id`，否则 403。

## 6. 文件上传安全

### 6.1 限制

- 单文件：图片 ≤ 50MB，视频 ≤ 200MB。通过 `Request` 流式读取 + `Content-Length` 预检，超限 413。
- 全局每用户存储配额（可选，环境变量控制）。

### 6.2 真实格式校验（不只看后缀）

1. 读取前 2KB 用 magic bytes / `filetype` 库判定真实类型。
2. 白名单：
   - 图片：`jpeg / png / webp / gif`
   - 视频：`mp4 / webm`
3. 禁止：任何可执行格式（`exe/elf/pe/...`）、脚本（`js/html/svg 内嵌脚本`）、压缩包内可执行。
4. 用 Pillow 重新编码图片（解码再保存），天然规避伪装/隐写；视频用 ffprobe 校验容器有效性（可选）。
5. 存储文件名用 `uuid4.ext`，原文件名仅存 DB。
6. 路径拼接用 `pathlib`，禁止拼接用户输入路径，防目录穿越。

### 6.3 缩略图（上传时生成多尺寸）

- 图片：用 Pillow 生成
  - `small`：长边 480px，WebP 质量 80 — 信息流加载。
  - `medium`：长边 1280px，WebP 质量 85 — 详情预览。
  - 原图保留。
- 视频：抽取首帧（或 1s 处）生成 `small` 缩略图 + 保存 `duration/metadata`。视频本身信息流用缩略图 + 播放图标，点击加载视频。
- 缩略图统一 WebP 格式，体积小、解码快。
- 存储结构：`data/uploads/2026/07/{uuid}.ext` + `data/uploads/2026/07/thumbs/{uuid}_small.webp`。

### 6.4 访问

- `GET /api/media/{media_id}/small|medium|original` → 经鉴权 + 可见范围校验后返回文件流。
- 静态资源经 FastAPI StaticFiles + 不可枚举，配 `html=False`、缓存头 `Cache-Control`。
- 原图与缩略图路径不直接暴露磁盘结构，通过 media_id 映射。

## 7. 安全防护清单

| 风险 | 措施 |
|------|------|
| 暴力破解登录 | slowapi 限流：登录 `5次/分钟/IP`，失败 5 次锁定该账号 15 分钟。 |
| 注册滥用 | 限流 `3次/小时/IP`；邀请码一次性/限量。 |
| 上传滥用 | 限流 `20次/小时/用户`；单文件大小校验。 |
| 密码传输 | 全站 HTTPS（TLS），密码不裸传明文；登录 body 经 TLS 加密，不再额外前端哈希（避免误导安全感）。 |
| 密码存储 | argon2，`memory_cost/time_cost/parallelism` 取安全默认。 |
| XSS | 文字/评论入库不做 HTML 处理；前端 React 默认转义，禁用 `dangerouslySetInnerHTML`；输出时再转义；CSP 头限制脚本源。 |
| SQL 注入 | 全部走 ORM 参数化查询，禁用裸字符串拼接 SQL。 |
| CSRF | 刷新令牌 cookie 用 `SameSite=Strict`；状态变更接口校验 `Authorization` header（非 cookie），天然防 CSRF。 |
| 越权 | 每个写接口校验资源所有权；可见范围由 `permissions.py` 统一判定。 |
| 目录穿越 | 文件名 UUID 化，路径用 `pathlib` 安全拼接。 |
| SPA 路由回退 | 对 `/api/*` 严格 404，不回退 index.html；非 API 的未知路径才回退到 SPA；避免把 API 路径误当前端路由。 |
| 信息泄露 | 生产关闭 debug，错误响应不暴露堆栈；日志脱敏（不记密码/token 明文）。 |
| 证书/密钥 | 自签证书私钥存 `data/ssl/` 并 `.gitignore`；`JWT_SECRET` 从环境变量注入。 |
| CORS | 单服务一体化，同源，默认不开 CORS（如需再按需白名单）。 |
| 依赖供应链 | `uv.lock` 锁定；前端 `package-lock`/`pnpm-lock` 锁定。 |

## 8. 配置管理

### 8.1 环境变量（`.env`）

```ini
# 应用
APP_ENV=production            # development|production
APP_HOST=0.0.0.0
APP_PORT=8443                 # HTTPS 端口
APP_URL=https://your-domain:8443

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./data/db/moment.sqlite3
# 切换 Postgres 示例:
# DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/moment

# JWT
JWT_SECRET=<openssl rand -hex 32>   # 必填，缺失拒绝启动
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# 文件上传
MAX_IMAGE_SIZE_MB=50
MAX_VIDEO_SIZE_MB=200
UPLOAD_DIR=./data/uploads

# 限流
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_REGISTER=3/hour
RATE_LIMIT_UPLOAD=20/hour

# 日志
LOG_DIR=./data/logs
LOG_LEVEL=INFO
```

### 8.2 配置加载

- `config.py` 用 Pydantic Settings，强类型校验，缺失关键项（如 `JWT_SECRET`）启动即失败。

## 9. HTTPS 与自签证书

- `ssl_gen.py`：启动时检测 `data/ssl/cert.pem`、`key.pem` 是否存在，不存在则用 `cryptography` 生成 RSA 2048 自签证书（SAN 含 `localhost`、`127.0.0.1`）。
- 本地开发可选：用 `mkcert -install` 生成本地受信任 CA，替换 `data/ssl/` 内证书，消除浏览器警告。
- 生产：预留环境变量 `SSL_CERT_FILE` / `SSL_KEY_FILE` 指向正式证书（如 Let's Encrypt），优先于自签。
- Uvicorn 以 `ssl_certfile` / `ssl_keyfile` 启动 HTTPS。

## 10. 静态资源与压缩

### 10.1 前端构建

- `scripts/build.sh`：`npm run build` → 产物输出 `frontend/dist`。
- Vite 插件 `vite-plugin-compression` 预生成 `.br` 和 `.gz`（`compressionLevel: brotli=11, gzip=9`）。
- 脚本将 `dist` 拷贝到 `backend/app/static`。

### 10.2 FastAPI 托管

- 启用 Brotli/Gzip 中间件：根据 `Accept-Encoding` 优先返回预压缩的 `.br`/`.gz`，未预压缩的再动态压缩。
- 静态文件挂载在根路径 `/`（`html=True` 用于 SPA 回退），`/api` 路由优先匹配。
- 路由顺序：**先注册所有 `/api/*` 路由，最后挂载 StaticFiles**，确保 API 命中。
- SPA 回退安全：对 `/api/*` 未匹配路径返回 404 JSON，不回退 index.html（见第 7 节）。

## 11. 启动脚本

### 11.1 `scripts/start.sh`（一键启动，Ctrl+C 全停）

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# 1. 前端构建（若 backend/app/static 不存在或过期）
if [ ! -d backend/app/static ] || [ "${FORCE_BUILD:-0}" = "1" ]; then
  bash scripts/build.sh
fi

# 2. 后端依赖安装
cd backend
uv sync
cd "$ROOT"

# 3. 启动后端（HTTPS），捕获子进程
trap 'kill 0' INT TERM EXIT
uv run uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8443}" \
  --ssl-certfile data/ssl/cert.pem --ssl-keyfile data/ssl/key.pem &
wait
```

- `trap 'kill 0' INT TERM EXIT`：Ctrl+C 时杀死进程组内所有子进程。
- 前后端同进程组，后端启动即托管前端，无需分别管理。

### 11.2 `scripts/build.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend"
npm install
npm run build
rm -rf "$ROOT/backend/app/static"
cp -r dist "$ROOT/backend/app/static"
```

## 12. 日志

- `logging_conf.py`：基于 `loguru`，配置轮转：
  - `data/logs/app.log`：应用日志，`10MB × 5` 轮转。
  - `data/logs/access.log`：访问日志（Uvicorn access）。
- 统一格式：`时间 | 级别 | 模块 | 请求ID | 消息`。
- 脱敏：禁止记录密码、token 明文；中间件可在请求头注入 `X-Request-Id` 贯穿日志。
- 全代码用 `from app.logging_conf import logger; logger.info(...)`。

## 13. 数据目录与 Docker 预留

- 所有可变数据在 `./data/`，Docker 映射 `-v ./data:/app/data` 即可。
- `Dockerfile`（后续提供）将前后端构建产物合并到单一镜像，仅暴露 8443。
- `.gitignore` 忽略 `data/`、`backend/app/static/`、`*.pem`、`.env`、`__pycache__`、`node_modules`。

## 14. API 路由概览

```
认证
  POST   /api/auth/register          邀请码注册        [限流]
  POST   /api/auth/login             登录              [限流]
  POST   /api/auth/refresh           刷新访问令牌
  POST   /api/auth/logout            登出

用户
  GET    /api/users/me               当前用户信息
  PATCH  /api/users/me               更新资料
  POST   /api/users/me/avatar         上传头像
  GET    /api/users/{id}             查看他人资料（受可见性限制的动态）

好友
  POST   /api/friends/requests       发起好友请求
  GET    /api/friends/requests        待处理请求
  POST   /api/friends/requests/{id}/{accept|reject}
  GET    /api/friends                好友列表
  DELETE /api/friends/{id}           删除好友

动态
  POST   /api/posts                  发布（支持先传 media 再关联）
  GET    /api/posts/feed              信息流（分页，返回 small 缩略图）
  GET    /api/posts/me                我的动态
  GET    /api/posts/{id}              动态详情（含 medium/原图链接）
  PATCH  /api/posts/{id}             编辑（仅作者）
  DELETE /api/posts/{id}             删除（仅作者）
  POST   /api/posts/{id}/visibility   修改可见范围

媒体
  POST   /api/media                   上传（返回 media_id + 缩略图链接） [限流]
  GET    /api/media/{id}/{small|medium|original}

评论
  POST   /api/posts/{id}/comments             发布顶级评论
  POST   /api/comments/{id}/replies           发布链式回复（parent_id=该评论）
  GET    /api/posts/{id}/comments             分页（按楼 root_id 聚合）
  GET    /api/comments/{id}/replies           分页加载某评论的子回复
  DELETE /api/comments/{id}                   软删（仅作者或动态作者）

点赞
  POST   /api/posts/{id}/likes
  DELETE /api/posts/{id}/likes
  POST   /api/comments/{id}/likes
  DELETE /api/comments/{id}/likes

管理员（可选）
  POST   /api/admin/invite-codes      生成邀请码
  GET    /api/admin/users
```

## 15. 前端关键设计

- 路由：`/`（信息流）、`/post/:id`、`/u/:username`、`/friends`、`/login`、`/register`、`/compose`。
- 信息流图片：默认渲染 `small` WebP 缩略图，点击放大用 `medium` 或原图（懒加载 `loading=lazy`）。
- 文字/评论：渲染前经 `utils/sanitize.ts` 转义（保险层），React 默认已转义，双重保障；不做富文本 HTML。
- 鉴权：axios 拦截器，401 自动调 refresh，失败跳登录页。
- 上传：分块/进度条，超限前端预检提示。
- 刷新令牌：httpOnly cookie 自动随请求携带，前端不可读。
- **链式评论展示**：按楼（`root_id`）分组渲染，楼内按 `parent_id` 组装树状缩进；深楼用「回复 @用户」平铺替代逐层缩进（`depth > MAX_DISPLAY_DEPTH` 时折叠为扁平列表），避免过深缩进；每楼默认显示前 N 条子回复 + 「展开更多」懒加载 `/api/comments/{id}/replies`；删除评论显示「该评论已删除」占位以维持树结构。

## 16. 实施阶段建议

1. **骨架**：目录、配置、DB 引擎、日志、证书生成、启动脚本、空跑 HTTPS。
2. **认证**：注册(邀请码)/登录/刷新/登出 + 限流 + argon2。
3. **用户/好友**：资料、好友请求、好友列表。
4. **媒体上传**：真实格式校验、缩略图、访问鉴权。
5. **动态**：发布、信息流、可见范围、详情、编辑/删除。
6. **评论 + 点赞**。
7. **前端**：路由、信息流、详情、个人页、好友、发布器。
8. **压缩/静态托管**：build 脚本、Brotli/Gzip、SPA 回退。
9. **加固**：CSP、错误脱敏、依赖锁定、Docker 预留。

## 17. 待确认 / 后续可扩展

- 头像、动态封面是否复用同一套 media 上传？→ 倾向是，复用 media 表（post_id 可空）。
- 是否需要「朋友圈式」单视图聚合（按时间线统一展示）？当前设计信息流按时间倒序，够用。
- 视频转码/自适应码率：当前不引入 ffmpeg 转码（仅抽帧缩略图），如需可后续加。
- 推送通知：暂不实现。
- 管理后台：仅提供邀请码生成接口，不做完整后台 UI。
- 头像/媒体删除时是否级联清理磁盘文件：实现清理任务，删除动态时异步删对应文件。