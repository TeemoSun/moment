## Project

Moments: a朋友圈-style social app. Two packages in one repo (not a monorepo workspace):

- `backend/` — Python 3.12 + FastAPI + SQLAlchemy 2.x, managed with **uv** (not pip). `backend/app/` is the app; `backend/alembic/` migrations; `backend/tests/` pytest suite. Run backend commands with `cd backend && uv run ...`.
- `frontend/` — React 18 + TS + Vite. `@/*` path alias → `frontend/src`. State via Zustand stores in `frontend/src/stores/`. Build = `tsc -b && vite build`.

Backend serves the built frontend (`frontend/dist`) in production; dev runs them separately. `docker compose up -d` runs the full stack (postgres:16 `db` service + backend `moments` service); backend auto-runs migrations on startup.

### Commands

Dev (both servers, Ctrl+C exits both): `bash scripts/dev.sh` — backend http://localhost:8000, frontend http://localhost:5173 (Vite proxies `/api` → backend; port via `VITE_BACKEND_PORT`). Backend connects to PostgreSQL via `DB_URL` (default `localhost:5432`); start PG first with `docker compose up -d db` or a local instance.

Build frontend: `bash scripts/build.sh`.

Backend lint/format/typecheck/test (run in `backend/`):
- `uv run ruff check app && uv run ruff format --check app && uv run ruff format --check alembic`
- `uv run mypy app`
- `uv run pytest` (tests need a **running PostgreSQL**; they use a shared `moments_test` DB reset via TRUNCATE between tests. Ensure PG is up — e.g. `docker compose up -d db` from repo root, or run a local PG on `localhost:5432` with the `POSTGRES_*` creds from `.env`).
  - ⚠️ `docker-compose.yml` 的 `db` 服务用 `expose`（仅容器间互通），**不映射宿主端口**。本地跑 pytest 时 Python 需经 `localhost:5432` 连库，因此要先让 PG 对宿主机可达：临时写一个 `docker-compose.override.yml`（gitignored，勿提交）映射端口后重启 db——
    ```yaml
    services:
      db:
        ports:
          - "5432:5432"
    ```
    然后 `docker compose down && docker compose up -d db`，并用 `docker exec moments-db pg_isready -U moments -d moments` 确认就绪再跑测试。用完可删除该 override 文件。
  - 若宿主机已自带监听 `localhost:5432` 的 PG（用 `.env` 的 `POSTGRES_*` 凭证可连），则无需 override，直接 `docker compose up -d db` 或用本地 PG 即可。
  - **测试结束后务必清理**：跑完 pytest 后执行 `docker compose down`（从仓库根目录）停掉并移除 db 容器及临时网络，删除 override 文件（如有），保持环境干净。
- single test: `uv run pytest tests/test_auth.py::TestClass::test_name -q`

Frontend lint/format (run in `frontend/`):
- `npm run lint -- --max-warnings=0` (ESLint, flat config)
- `npx prettier --check "src/**/*.{ts,tsx,css}"`; write with `npm run format`
- typecheck: `npm run build` runs `tsc -b` (no standalone `typecheck` script)

Pre-commit hook (.githooks/pre-commit) runs the backend ruff/mypy + frontend eslint/prettier checks above. Enable once with `git config core.hooksPath .githooks`.

### Backend gotchas

- **Migrations auto-run on startup.** `app.main:lifespan` calls `alembic upgrade head` via `app.main._run_alembic_upgrade()`. Set `SKIP_ALEMBIC=1` to skip it (tests do). The Dockerfile relies on this — it does NOT run migrations itself.
- **`.env` is mutated at runtime.** `app.config.ensure_runtime_env()` (called in lifespan and `alembic/env.py`) creates `.env` from `.env.example` if missing and auto-generates + writes `JWT_SECRET` (chmod 0600) when empty. Don't assume `.env` is read-only.
- **All ORM models must be imported** in `app/models/__init__.py` so Alembic's `Base.metadata` sees them. `alembic/env.py` does `import app.models`; the test conftest does the same before `Base.metadata.create_all`.
- **`bcrypt<4` is pinned** (passlib compatibility) — don't upgrade blindly.
- **Database is PostgreSQL** (psycopg 3 driver, `postgresql+psycopg://` URLs). `app/database.py` uses a connection pool (`pool_pre_ping`, `pool_size=5`, `max_overflow=10`); do not re-add SQLite-specific `PRAGMA`/`check_same_thread` code. Driver is `psycopg[binary]` (bundled libpq, no system libpq needed).
- **Video handling needs ffmpeg/ffprobe** on PATH (`app/storage/filekit.py` validates videos with `ffprobe`). The Docker image installs `ffmpeg`; local dev must have it too.
- Migrations target PostgreSQL (`alembic/env.py` no longer uses `render_as_batch=True`; that was SQLite-only). `server_default` uses `func.now()`, not `text("CURRENT_TIMESTAMP")`.
- Config is `pydantic-settings` (`app.config.Settings`); `settings` is a module-level singleton but tests/`lifespan` reassign it via `cfg.settings = cfg._create_settings()` after env changes — mutate env then re-create settings rather than editing the singleton.

### Frontend gotchas

- **`animal-island-ui` is bundled** by Vite via its npm package (ESM entry in `package.json` `exports`). Imports like `import { Card } from "animal-island-ui"` resolve to the local ES module; CSS comes from `import "animal-island-ui/style"` in `main.tsx`. No CDN/global is used. When building UI in this repo, load the `animal-island-ui-style` skill for its conventions.
- **Fonts are self-hosted** via `@fontsource-variable/nunito` and `@fontsource-variable/noto-sans-sc` (imported via `wght.css` in `main.tsx` as variable fonts covering all weights). CSS `--animal-font-family` uses `'Nunito Variable'` / `'Noto Sans SC Variable'`. Do not re-add Google Fonts CDN links to `index.html`. Use the `@fontsource-variable/*` packages (which bundle woff2); the non-variable `@fontsource/*` packages for these fonts ship only woff, which breaks under the Vite SPA fallback.
- Passwords are RSA-encrypted client-side before sending (`frontend/src/utils/rsa.ts` + `jsencrypt`); backend decrypts with `app/services/rsa_service.py` (key pair warmed up at startup via `_warmup_rsa`). Don't send plaintext passwords.
- Vite dev server proxies `/api` → `http://localhost:${VITE_BACKEND_PORT}` (default 8000).

### Env

`.env` is gitignored and mostly self-bootstrapping; see `.env.example` for the full list. Notable: `DEBUG`, `SECURE_COOKIES`, `DB_URL` (default `postgresql+psycopg://moments:moments@localhost:5432/moments`), `POSTGRES_*` (user/password/db/host/port — used by docker-compose to start the `postgres:16` service and by tests to locate the DB), `JWT_SECRET` (auto-generated if empty), `CORS_ORIGINS` (comma-separated, empty = no CORS), `STORAGE_ROOT`, media size limits, `PUBLIC_BASE_URL` (used for invite links).

### Layout notes

- `storage/` — runtime media files (gitignored). `data/` — PostgreSQL data (`data/pg`, gitignored). `logs/` — runtime logs (gitignored). `docs/` — design docs (Chinese): `项目实现方案.md` is the detailed spec.
- API routes mounted under `/api`; docs at `/api/docs`, OpenAPI at `/api/openapi.json`.
- App layers: `app/api/` (routers), `app/services/` (business logic), `app/models/` (ORM), `app/schemas/` (Pydantic), `app/storage/` (media/ffprobe/filekit), `app/tasks/`, `app/core/`, `app/utils/`.
- `system_status` table holds the single init/admin row; `_ensure_system_status()` in `main.py` inserts the seed row idempotently at startup.

## tools
###  CodeGraph

Reach for CodeGraph BEFORE grep/find or reading files when you need to understand or locate code (requires a `.codegraph/` directory at the repo root).

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.




## coding rule


**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.


### 1. Think Before Coding


**Don't assume. Don't hide confusion. Surface tradeoffs.**


Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.


### 2. Simplicity First


**Minimum code that solves the problem. Nothing speculative.**


- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.


Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.


### 3. Surgical Changes


**Touch only what you must. Clean up only your own mess.**


When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.


When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.


The test: Every changed line should trace directly to the user's request.


### 4. Goal-Driven Execution


**Define success criteria. Loop until verified.**


Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"


For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.



## 针对较大规模改动的工作规范

### 1. 变更规模判定
在执行任何代码修改前，必须先预估编辑行数：
- **小规模修改**：预估编辑量 ≤ 40 行
- **大规模修改**：预估编辑量 > 40 行

### 2. 执行策略

#### 2.1 小规模修改（≤ 40 行）
- **直接执行**：无需额外审批或方案设计，直接完成代码修改。
- **验证**：修改后进行基本的正确性自查。

#### 2.2 大规模修改（> 40 行）
必须严格遵循以下**六步闭环流程**，禁止跳步：

1. **分析**：深入理解现有代码结构、依赖关系及潜在影响面。
2. **方案**：输出完整、详细的实现方案（含改动点、风险点、回滚策略）。
3. **编码**：调用 `tool-agent` 按方案执行代码编写。
4. **评审**：由主Agent对 `tool-agent` 的产出进行代码审查，识别缺陷与偏差。
5. **修复**：根据评审问题，得到修复方案，交给 `tool-agent` 进行定向修复。
6. **兜底**：检查修复质量，对遗留问题进行最终兜底修复，确保交付物可用。

### 3. 注意事项
- 规模判定以**预估有效编辑行数**为准，不含空行与纯注释。
- 凭感觉快速大致估计行数即可，不需要严谨计算。
- 大规模修改流程中，若评审发现方案级缺陷，应回退至步骤2重新设计方案，而非在步骤5中强行修补。
- `tool-agent` 仅作为编码执行器，分析与评审环节必须由主Agent主导完成。



## Docker 镜像打包上传

当用户要求打包/上传 Docker 镜像到 Docker Hub 时，务必遵循 `docs/Docker镜像打包上传.md` 的完整流程。要点：

- 多阶段 `Dockerfile`（前端 build + 后端 runtime）位于仓库根目录，构建命令在根目录执行。
- tag 规范：同时打 `<user>/moments:latest` 与 `<user>/moments:<YYYYMMDD>`（当日日期）。本项目 Docker Hub 用户名为 `pigzho`。
- 流程：`docker build` → `docker login`（已登录可跳过）→ `docker push` 两个 tag。
- 删除远程 tag 需走 Docker Hub API（带 JWT），详见文档；本地删除用 `docker rmi`。
- 不要使用 `git commit hash` 作为 tag，统一用日期 tag。
