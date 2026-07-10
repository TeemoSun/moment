# Moment 技术方案设计

> 类朋友圈 Web 应用，FastAPI + React，SQLite（ORM 可切换），邀请码注册，JWT 鉴权。

---

## 1. 需求概览

| 维度 | 说明 |
|------|------|
| 核心功能 | 发布动态（图片/视频/文字），信息流浏览，评论（一层嵌套回复），点赞，好友关系 |
| 可见性 | 动态可设为「公开」或「仅好友」 |
| 注册 | 邀请码注册，凭邀请码才可创建账号 |
| 后台 | 完整管理后台：用户管理、内容审核、邀请码管理、数据统计 |
| 媒体 | 文件存固定文件夹，DB 只存元数据；图片 Pillow 生成缩略图，视频 ffmpeg 提取首帧 |
| 安全 | 文件真实格式校验、禁可执行文件、限文件大小；XSS 转义；接口鉴权防越权；登录加密 |
| 部署 | HTTPS 自签证书起步，后续 nginx 反代；规模小，架构规范优先，不追求极致性能 |

## 2. 已确认的技术决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 注册模式 | 邀请码注册 | 防公网恶意注册，适合小圈子 |
| 互动功能 | 评论 + 点赞 + 一层嵌套回复 | 兼顾功能与复杂度 |
| 视频缩略图 | ffmpeg 提取首帧 | 体验最好，需服务器装 ffmpeg |
| 前端栈 | React + TypeScript + Vite + Ant Design | 类型安全 + 组件齐全 |
| 鉴权 | JWT 存 httpOnly Cookie | 防 XSS 窃取，nginx 友好 |
| 后台 | 完整后台 | 用户/内容/邀请码/统计管理 |

## 3. 技术栈

### 后端
- **FastAPI** + **Uvicorn**（ASGI，支持 HTTPS）
- **SQLAlchemy 2.0**（async ORM，通过连接串切换 SQLite/PostgreSQL/MySQL）
- **Alembic** 数据库迁移
- **Pydantic v2** 数据校验
- **PyJWT** 生成/校验 JWT
- **passlib[argon2]** 密码哈希
- **Pillow** 图片处理与缩略图
- **ffmpeg/ffprobe**（系统命令调用）视频首帧提取与格式探测
- **python-magic** 文件魔术字节校验（真实格式探测）
- **aiosqlite** 异步 SQLite 驱动

### 前端
- **React 18** + **TypeScript**
- **Vite** 构建工具
- **Ant Design 5** UI 组件库
- **Axios** HTTP 客户端（withCredentials 携带 Cookie）
- **DOMPurify** 富文本/用户输入净化（XSS 防护）
- **React Query** 服务端状态管理（缓存、分页加载）
- **dayjs** 时间格式化
- **zustand** 轻量客户端状态（登录态等）

### 部署
- **OpenSSL** 生成自签证书
- **nginx** 反向代理（生产）
- **Docker / docker-compose**（可选，便于部署）

## 4. 系统架构

```
┌─────────────────────────────────────────────────────┐
│                     浏览器                          │
│  React SPA (Vite 构建)                               │
│  - DOMPurify 转义用户内容                            │
│  - Axios withCredentials (Cookie 携带 JWT)          │
└───────────────┬─────────────────────────────────────┘
                │ HTTPS (生产经 nginx 反代)
                ▼
┌─────────────────────────────────────────────────────┐
│              nginx (反代 + TLS 终结)                 │
│  - 前端静态资源直接服务                               │
│  - /api → 后端                                       │
│  - /uploads → 静态文件 (或后端代理)                   │
└───────────────┬─────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI (Uvicorn)                       │
│  ├── 认证中间件 (JWT 校验, 从 Cookie 读取)            │
│  ├── API 路由 (auth/users/posts/comments/...)        │
│  ├── Service 层 (业务逻辑)                           │
│  └── 文件处理服务 (校验/缩略图/存储)                   │
└───────┬───────────────────────┬─────────────────────┘
        │                       │
        ▼                       ▼
┌──────────────┐      ┌──────────────────────┐
│  SQLite (ORM)│      │  本地文件系统          │
│  SQLAlchemy  │      │  uploads/             │
│  Alembic     │      │  ├── originals/       │
│              │      │  └── thumbnails/      │
└──────────────┘      └──────────────────────┘
```

### 请求流程（信息流）
1. 前端加载动态列表，后端返回动态 + 缩略图相对路径
2. 前端渲染缩略图（小尺寸，快速加载）
3. 用户点击图片，前端请求原图 URL 加载完整图
4. 视频同理：缩略图占位，点击加载视频源

## 5. 目录结构

```
moment/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI 应用入口，路由挂载，中间件
│   │   ├── core/
│   │   │   ├── config.py                 # 配置项（环境变量读取）
│   │   │   ├── security.py               # 密码哈希、JWT 生成/校验
│   │   │   ├── database.py              # SQLAlchemy 引擎、Session 工厂
│   │   │   └── dependencies.py          # FastAPI 依赖注入（当前用户、分页）
│   │   ├── models/                       # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py                   # DeclarativeBase, 公共 Mixin
│   │   │   ├── user.py
│   │   │   ├── post.py
│   │   │   ├── comment.py
│   │   │   ├── like.py
│   │   │   ├── friendship.py
│   │   │   ├── media.py                 # 媒体文件元数据
│   │   │   ├── invite_code.py          # 邀请码 + 使用记录
│   │   │   └── refresh_token.py         # 可吊销刷新令牌
│   │   ├── schemas/                      # Pydantic 请求/响应模型
│   │   │   ├── user.py
│   │   │   ├── post.py
│   │   │   ├── comment.py
│   │   │   ├── auth.py
│   │   │   └── common.py                # 分页、统一响应
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routers/
│   │   │       ├── auth.py              # 注册/登录/登出/刷新
│   │   │       ├── users.py             # 用户资料、好友操作
│   │   │       ├── posts.py             # 动态 CRUD + 信息流
│   │   │       ├── comments.py          # 评论/回复 CRUD
│   │   │       ├── likes.py             # 点赞
│   │   │       ├── friendships.py       # 好友请求/列表
│   │   │       ├── uploads.py          # 文件上传
│   │   │       └── admin.py            # 后台管理接口
│   │   ├── services/
│   │   │   ├── upload_service.py        # 文件校验、缩略图、存储
│   │   │   ├── post_service.py          # 动态业务逻辑
│   │   │   ├── friendship_service.py    # 好友关系逻辑
│   │   │   ├── permission_service.py    # 可见性/越权校验
│   │   │   └── cleanup_service.py      # 孤儿文件清理定时任务
│   │   └── utils/
│   │       ├── file_utils.py            # 文件类型校验、路径处理
│   │       └── media_utils.py           # Pillow 缩略图、ffmpeg 调用
│   ├── alembic/                         # 数据库迁移
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_posts.py
│   │   └── test_uploads.py
│   ├── uploads/                         # 上传文件根目录（gitignore）
│   │   ├── originals/                   # 按年月分目录: 2024/01/
│   │   └── thumbnails/
│   ├── certs/                           # 自签证书（gitignore）
│   ├── requirements.txt
│   ├── .env.example
│   └── run.sh                            # 启动脚本
├── frontend/
│   ├── src/
│   │   ├── api/                          # API 调用封装
│   │   │   ├── client.ts                 # Axios 实例
│   │   │   ├── auth.ts
│   │   │   ├── posts.ts
│   │   │   └── ...
│   │   ├── components/
│   │   │   ├── PostCard.tsx
│   │   │   ├── PostForm.tsx
│   │   │   ├── CommentList.tsx
│   │   │   ├── MediaViewer.tsx           # 缩略图→原图切换查看
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Feed.tsx                  # 信息流
│   │   │   ├── Profile.tsx
│   │   │   ├── PostDetail.tsx
│   │   │   └── admin/                    # 后台页面
│   │   ├── hooks/
│   │   ├── store/                        # zustand
│   │   ├── types/                        # TS 类型定义
│   │   ├── utils/
│   │   │   └── sanitize.ts              # DOMPurify 封装
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── scripts/
│   ├── generate_certs.sh                # 生成自签证书
│   └── create_admin.py                  # 创建管理员账号
├── nginx/
│   └── nginx.conf.example
├── docs/
│   └── DESIGN.md                        # 本文档
├── .gitignore
└── README.md
```

## 6. 数据模型设计

### 6.1 ER 关系概览

```
User 1───* Post            (一个用户发多条动态)
User 1───* Comment         (一个用户发多条评论)
Post 1───* Comment         (一条动态有多条评论)
Comment 1──* Comment       (评论的子回复，一层嵌套)
User 1───* Like ─* Post    (用户对动态点赞，多对多)
Post 1───* Media            (一条动态可含多个媒体文件)
User 1───* Friendship *──1 User  (好友关系，双向)
User 1───* InviteCode       (管理员生成邀请码)
InviteCode 1───* InviteCodeUsage  (邀请码使用记录)
User 1───* RefreshToken      (可吊销的刷新令牌)
```

### 6.2 表结构

#### users
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| username | String(50) unique | 用户名，唯一 |
| email | String(255) unique | 邮箱 |
| password_hash | String(255) | argon2 哈希 |
| display_name | String(50) | 昵称 |
| avatar_path | String(255) nullable | 头像相对路径 |
| bio | Text nullable | 个人简介 |
| is_admin | Boolean default False | 是否管理员 |
| is_active | Boolean default True | 是否启用（封禁用） |
| created_at | DateTime | |
| updated_at | DateTime | |

#### invite_codes
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| code | String(32) unique | 邀请码 |
| created_by | FK users | 生成者（管理员） |
| max_uses | Integer default 1 | 最大可使用次数（0 = 不限次） |
| use_count | Integer default 0 | 已使用次数 |
| expires_at | DateTime | 过期时间 |
| created_at | DateTime | |

> 单个邀请码可被多人使用（`use_count < max_uses` 或 `max_uses = 0`）。已达到上限的邀请码拒绝使用。每次使用在 `invite_code_usages` 表记录使用者。

#### invite_code_usages
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| invite_code_id | FK invite_codes | 使用的邀请码 |
| user_id | FK users | 使用者（注册的新用户） |
| used_at | DateTime | 使用时间 |

> 联合唯一约束：(invite_code_id, user_id) 防止同一用户重复使用同一码。

#### posts
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| user_id | FK users | 发布者 |
| content | Text nullable | 文字内容（可纯文字动态） |
| visibility | Enum(public, friends_only) | 可见范围 |
| created_at | DateTime | |
| updated_at | DateTime | |

#### media
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| post_id | FK posts | 所属动态 |
| user_id | FK users | 上传者 |
| file_name | String(255) | 存储文件名（UUID + 扩展名） |
| original_path | String(512) | 原图/原视频相对路径 |
| thumbnail_path | String(512) nullable | 缩略图相对路径 |
| file_size | Integer | 原文件字节大小 |
| mime_type | String(100) | 真实 MIME 类型 |
| file_format | String(50) | 检测到的真实格式 |
| width | Integer nullable | 图片/视频宽 |
| height | Integer nullable | 图片/视频高 |
| duration | Float nullable | 视频时长（秒） |
| media_type | Enum(image, video) | 媒体类型 |
| sort_order | Integer | 动态内媒体排列顺序 |
| created_at | DateTime | |

#### comments
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| post_id | FK posts | 所属动态 |
| user_id | FK users | 评论者 |
| parent_id | FK comments nullable | 父评论 ID（一层嵌套） |
| content | Text | 评论内容 |
| created_at | DateTime | |
| updated_at | DateTime | |

> 约束：`parent_id` 指向的评论 `parent_id` 必须为 NULL，确保只嵌套一层（业务层校验）。
> **删除策略**：删除顶级评论时级联删除其所有子回复（业务层实现，SQLite 默认无外键级联）。删除子回复不影响父评论。禁止删除有子回复的顶级评论前必须先处理子回复——实现采用「删父连带删子」简化操作。

#### likes
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| user_id | FK users | |
| post_id | FK posts | |
| created_at | DateTime | |

> 联合唯一约束：(user_id, post_id)

#### friendships
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| requester_id | FK users | 发起好友请求者 |
| addressee_id | FK users | 被请求者 |
| status | Enum(pending, accepted, blocked) | |
| created_at | DateTime | |
| accepted_at | DateTime nullable | |

> 联合唯一约束：(requester_id, addressee_id)
> 查询好友时双向查：A 加 B 或 B 加 A，status=accepted
> **写入规范化**：发起请求时强制 `requester_id < addressee_id`（即始终把 ID 较小者作为 requester）。如此 (A,B) 与 (B,A) 归一为同一行，唯一约束即可拦截重复请求。发起请求前先查该方向是否存在 pending 记录：若已存在则提示「已发送请求」；若被请求方已反向发起 pending，则发起方应改为直接 accept 该记录而非新建。

#### refresh_tokens
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| user_id | FK users | 所属用户 |
| jti | String(36) unique | JWT ID，与 refresh_token 的 jti 对应 |
| is_revoked | Boolean default False | 是否已吊销（登出/封禁时置 True） |
| expires_at | DateTime | 过期时间 |
| created_at | DateTime | |
| last_used_at | DateTime nullable | 最近一次刷新时间 |

> 每次刷新时校验 DB 中对应 jti 存在且 `is_revoked = False` 且未过期。登出时吊销当前 jti；封禁用户时批量吊销其所有未过期 refresh_token。刷新后可选地吊销旧 jti、签发新 jti（rotation）。

## 7. 核心模块设计

### 7.1 认证授权

**注册流程（邀请码）：**
1. 管理员在后台生成邀请码（可设过期时间、最大使用次数，0 = 不限次）
2. 用户注册时提交：username、email、password、invite_code
3. 后端校验邀请码有效性：未过期、`use_count < max_uses`（或 `max_uses = 0`）
4. 密码用 argon2 哈希存储；创建用户后 `use_count += 1`，并在 `invite_code_usages` 表写入使用记录
5. 创建用户，返回 JWT（设 httpOnly Cookie）

**登录流程：**
1. 提交 username + password（HTTPS 传输加密）
2. 后端校验密码（passlib verify）
3. 生成 access_token（短时，如 2h）+ refresh_token（长时，如 7d）
4. 双 token 均设 httpOnly + Secure + SameSite=Lax Cookie
5. refresh_token 存 DB（token 表或 Redis，便于吊销）

**JWT 设计：**
- payload: `{ "sub": user_id, "is_admin": bool, "exp": ..., "jti": ... }`
- access_token: 短过期，存 Cookie `access_token`
- refresh_token: 长过期，存 Cookie `refresh_token`，DB 记录 jti 可吊销
- 每次请求从 Cookie 读取 access_token 校验；过期则用 refresh_token 换新

**鉴权中间件/依赖：**
- `get_current_user`: 解析 Cookie 中的 JWT，返回 User 或 401
- `get_current_active_user`: 额外校验 is_active
- `require_admin`: **查 DB 校验当前用户 `is_admin && is_active`**，否则 403。不以 JWT 中的 is_admin 为最终依据（防降级/封禁后的提权窗口）。token 中的 is_admin 仅用于快速预筛。

**越权防护：**
- 修改/删除动态、评论前校验 `resource.user_id == current_user.id`（或 admin）
- 好友请求只能操作自己相关的记录
- 后台接口必须 `require_admin`（查库校验，见上）

### 7.2 文件上传与处理

**安全校验链（多重防护）：**

1. **大小限制**
   - 图片：单文件 ≤ 10MB
   - 视频：单文件 ≤ 100MB
   - 配置项可调，后端在接收时早截断（不读全量到内存）

2. **真实格式校验（不只看后缀）**
   - 用 `python-magic` 读取文件头部魔术字节判断真实 MIME
   - 图片额外用 Pillow `Image.open()` 尝试解码验证（防伪造）
   - 视频用 `ffprobe` 探测真实格式
   - 校验后端声明的 content-type 与真实类型一致

3. **禁止类型**
   - 黑名单：`.exe .bat .cmd .sh .php .js .py .jar .dll .so` 等可执行/脚本
   - 白名单（推荐）：只允许 `image/jpeg, image/png, image/webp, image/gif, video/mp4, video/webm`
   - 采用白名单策略更安全

4. **文件名安全**
   - 重命名为 `uuid4().hex + .{ext}`，不使用用户原始文件名
   - 存储路径：`uploads/originals/{年}/{月}/{uuid}.{ext}`

5. **存储隔离**
   - originals 与 thumbnails 分离
   - nginx 配置 originals 不执行、不列出目录

**缩略图生成：**
- 图片：Pillow resize，长边 ≤ 400px，保持比例，保存为 WebP（体积小）
- 视频：ffmpeg 提取首帧 `-ss 00:00:01 -frames:v 1`，再生成缩略图
- 缩略图路径：`uploads/thumbnails/{年}/{月}/{uuid}_thumb.webp`

**上传接口流程：**
```
POST /api/uploads
├── 校验认证
├── 读取文件流（限制大小）
├── python-magic 探测真实类型
├── 白名单校验
├── 生成 UUID 文件名
├── 存储原图到 originals/
├── 生成缩略图到 thumbnails/
├── 提取元数据（尺寸、时长）
├── 写入 media 表
└── 返回 media_id + 缩略图路径（创建动态时引用）
```

> 上传与发布分离：先上传文件获得 media_id，发布动态时携带 media_id 列表。
> **孤儿文件清理**：上传后未在 1 小时内关联到 post 的 media 记录标记为孤儿；后台定时任务（每小时扫描）删除孤儿 media 的磁盘文件并清理 DB 记录。删除动态时同步删除其关联 media 的磁盘文件（原图 + 缩略图）。

### 7.3 好友关系

**好友请求流程：**
1. A 发起请求，规范化为 `(min(A,B), max(A,B))` → friendships(requester=min, addressee=max, status=pending)
2. B 收到通知 → 接受则 status=accepted，拒绝则删除记录
3. accepted 后双方互为好友
4. 若 A 发起时发现 B 已反向 pending，则跳过新建、直接 accept 现有记录（避免双向重复）

**好友列表查询：**
```sql
SELECT * FROM friendships
WHERE (requester_id = :uid OR addressee_id = :uid)
  AND status = 'accepted'
```

**动态可见性逻辑（信息流）：**
- `visibility = public`：所有登录用户可见
- `visibility = friends_only`：仅本人 + 好友可见
- 查询条件（当前用户 uid 看动态）：
```sql
WHERE post.user_id = :uid                                    -- 自己的
   OR post.visibility = 'public'                              -- 公开
   OR (post.visibility = 'friends_only'                       -- 仅好友
       AND EXISTS (好友关系 WHERE 双方 = uid AND post.user_id))
```

### 7.4 评论与嵌套回复

- 顶级评论：`parent_id = NULL`
- 回复：`parent_id` 指向顶级评论（一层）
- 业务约束：回复的 parent 必须是顶级评论（parent.parent_id == NULL）
- 列表查询：先查顶级评论（分页），再批量查各顶级评论的子回复（避免 N+1）

### 7.5 点赞

- 用户对动态点赞/取消点赞（toggle）
- `likes` 表联合唯一约束防止重复
- 动态列表返回 `like_count` + `is_liked`（当前用户是否已赞）

## 8. 安全策略

### 8.1 认证与加密
| 项 | 措施 |
|----|------|
| 密码存储 | argon2 哈希（passlib），不存明文 |
| 登录传输 | HTTPS 加密通道；密码前端不额外加密（HTTPS 已保证，二次加密无意义且增加复杂度） |
| JWT 存储 | httpOnly + Secure + SameSite Cookie，前端 JS 无法读取 |
| Token 刷新 | access 短期 + refresh 长期，refresh 可吊销 |
| 暴力破解 | 登录失败计数，超过阈值临时锁定（如同 IP 5 次失败锁 15min） |

### 8.2 文件上传安全
| 项 | 措施 |
|----|------|
| 真实格式 | python-magic 魔术字节 + Pillow 解码验证 + ffprobe |
| 类型限制 | 白名单：jpeg/png/webp/gif/mp4/webm |
| 可执行文件 | 白名单天然拦截，额外黑名单兜底 |
| 文件大小 | 图片 10MB / 视频 100MB，配置可调 |
| 文件名 | UUID 重命名，杜绝路径穿越 |
| 存储目录 | nginx 配 `location /uploads` 禁止执行脚本 |

### 8.3 XSS 防护
| 项 | 措施 |
|----|------|
| 文本渲染 | React 默认对 `{}插值转义，不使用 dangerouslySetInnerHTML 渲染用户内容 |
| 富文本 | 若需富文本，用 DOMPurify 净化后再渲染 |
| Cookie | httpOnly 防 JS 读取；SameSite 防 CSRF |
| CSP | nginx 配置 Content-Security-Policy 头 |

### 8.4 接口鉴权与越权防护
| 项 | 措施 |
|----|------|
| 鉴权 | 需登录接口挂 `get_current_user`；后台挂 `require_admin` |
| 资源归属校验 | 增删改前校验 `resource.user_id == current_user.id` |
| 可见性校验 | 查看他人仅好友动态前校验好友关系 |
| ID 遍历防护 | 不暴露自增 ID 为主键 URL？使用 ID 但配合归属校验 |
| 速率限制 | 登录、注册、上传接口加速率限制 |

### 8.5 其他
- **CORS**：严格白名单，仅允许前端域名（生产经 nginx 同源可禁用 CORS）
- **SQL 注入**：全用 ORM 参数化查询，不拼 SQL
- **日志**：不记录密码、token 等敏感信息
- **依赖安全**：pip-audit / npm audit 定期扫描

## 9. API 设计

### 9.1 统一响应格式
```json
{
  "code": 0,        // 0 成功，非 0 错误码
  "message": "ok",
  "data": { ... }   // 成功数据，错误时为 null
}
```

### 9.2 接口列表

#### 认证
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | /api/auth/register | 注册（含邀请码） | 无 |
| POST | /api/auth/login | 登录 | 无 |
| POST | /api/auth/logout | 登出 | 是 |
| POST | /api/auth/refresh | 刷新 token | refresh cookie |
| GET | /api/auth/me | 获取当前用户信息 | 是 |

#### 用户
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/users/{username} | 查看用户资料 |
| PUT | /api/users/me | 更新自己的资料 |
| POST | /api/users/me/avatar | 上传头像 |
| GET | /api/users/me/friends | 我的好友列表 |

#### 好友
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/friendships/requests | 发起好友请求 |
| GET | /api/friendships/requests/pending | 收到的好友请求 |
| POST | /api/friendships/requests/{id}/accept | 接受请求 |
| POST | /api/friendships/requests/{id}/reject | 拒绝请求 |
| DELETE | /api/friendships/{friend_id} | 删除好友 |
| GET | /api/friendships/suggestions | 可能认识的人（可选） |

#### 动态
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/posts | 发布动态（含 media_ids） |
| GET | /api/posts/feed | 信息流（分页，按可见性过滤） |
| GET | /api/posts/feed/following | 好友动态流（可选独立接口） |
| GET | /api/posts/{id} | 动态详情 |
| PUT | /api/posts/{id} | 编辑动态 |
| DELETE | /api/posts/{id} | 删除动态 |
| GET | /api/users/{username}/posts | 某用户的动态列表 |

#### 评论
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/posts/{id}/comments | 评论列表（含子回复） |
| POST | /api/posts/{id}/comments | 发评论（可带 parent_id） |
| PUT | /api/comments/{id} | 编辑评论 |
| DELETE | /api/comments/{id} | 删除评论 |

#### 点赞
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/posts/{id}/like | 点赞 |
| DELETE | /api/posts/{id}/like | 取消点赞 |

#### 上传
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/uploads | 上传文件，返回 media_id + 缩略图路径 |

#### 后台管理（require_admin）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/admin/users | 用户列表 |
| PUT | /api/admin/users/{id}/status | 启用/封禁用户 |
| GET | /api/admin/posts | 所有动态（含审核） |
| DELETE | /api/admin/posts/{id} | 删除违规动态 |
| DELETE | /api/admin/comments/{id} | 删除违规评论 |
| POST | /api/admin/invite-codes | 生成邀请码 |
| GET | /api/admin/invite-codes | 邀请码列表 |
| GET | /api/admin/stats | 数据统计（用户数/动态数等） |

## 10. HTTPS 与部署

### 10.1 自签证书生成
```bash
# scripts/generate_certs.sh
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout certs/key.pem -out certs/cert.pem \
  -days 365 -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

开发阶段 Uvicorn 直接用自签证书启动 HTTPS：
```bash
uvicorn app.main:app --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
```

### 10.2 nginx 反代配置（生产）
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # 安全响应头
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none';" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 前端静态资源
    root /var/www/moment/dist;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反代
    location /api/ {
        proxy_pass https://127.0.0.1:8000;  # 或 http 如果后端不启用 TLS
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;

        # 上传大小限制
        client_max_body_size 110M;

        # WebSocket 支持（如将来用）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 上传文件静态服务（禁执行）
    location /uploads/ {
        alias /app/backend/uploads/;
        add_header Content-Disposition "inline";
        # 禁止执行
        location ~* \.(php|py|sh|exe|js)$ {
            deny all;
        }
    }
}

# HTTP 重定向 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}
```

> 生产环境后端可不开 HTTPS，由 nginx 终结 TLS，后端走 http。Cookie 需配合 `Secure` 标志——经 nginx 反代时后端通过 `X-Forwarded-Proto` 判断是否安全连接。

### 10.3 环境变量配置
```env
# backend/.env.example
DATABASE_URL=sqlite+aiosqlite:///./data/moment.db
# 必须替换为随机生成的强密钥（≥32 字节）。应用启动时校验：若等于示例占位符或长度不足 32 字节则拒绝启动。
JWT_SECRET_KEY=change-me-to-random-256-bit
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_DAYS=7

UPLOAD_DIR=./uploads
MAX_IMAGE_SIZE_MB=10
MAX_VIDEO_SIZE_MB=100

# 生产关闭自签，用 nginx
USE_SSL=true
SSL_KEY_FILE=./certs/key.pem
SSL_CERT_FILE=./certs/cert.pem

# CORS（生产同源可不配）
CORS_ORIGINS=https://your-domain.com

# 登录保护
LOGIN_FAIL_MAX=5
LOGIN_LOCK_MINUTES=15
```

## 11. 开发计划与里程碑

| 阶段 | 内容 | 产出 |
|------|------|------|
| **M1** | 项目骨架、配置、DB 模型、迁移 | 可运行的空项目，表结构就绪 |
| **M2** | 认证模块（注册/登录/JWT/邀请码） | 用户可注册登录 |
| **M3** | 文件上传服务（校验/缩略图/存储） | 安全上传 + 缩略图 |
| **M4** | 动态 CRUD + 信息流 + 可见性 | 核心功能可用 |
| **M5** | 评论/嵌套回复 + 点赞 | 互动功能完整 |
| **M6** | 好友关系（请求/接受/列表） | 社交关系可用 |
| **M7** | 前端全部页面 + 组件 | 可交互的完整 UI |
| **M8** | 后台管理模块 | 管理功能完整 |
| **M9** | 安全加固、测试、部署配置 | 可上线 |

## 12. 关键依赖清单

### backend/requirements.txt
```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]>=2.0
alembic
aiosqlite
pydantic>=2
pydantic-settings
pyjwt
passlib[argon2]
Pillow
python-magic
python-multipart    # 文件上传
slowapi             # 速率限制
```

系统依赖：`libmagic`、`ffmpeg`、`openssl`

### frontend/package.json
```
react react-dom
typescript
vite
antd
axios
@tanstack/react-query
dayjs
zustand
dompurify
```

## 13. 待确认 / 可调整项

1. **密码登录是否需要前端二次加密**：HTTPS 已保证传输安全，前端二次加密无实际安全增益且增加复杂度。方案默认不做，仅 HTTPS。如需可加 RSA 前端加密。

2. **动态是否支持纯文字**：当前设计支持（content 可无 media）。确认。

3. **头像存储**：复用上传服务存 uploads/，DB 存相对路径。

4. **删除策略**：硬删除。小规模应用无需软删除，如需可加 `deleted_at`。

5. **通知系统**：好友请求、评论、点赞是否需要通知？当前未列入，可后续加。

6. **分页方式**：offset 分页（小规模够用），如需可改游标分页。

---

*文档完成后将作为开发依据，按里程碑顺序实现。如有调整请提出。*