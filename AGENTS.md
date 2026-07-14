## Project

Moments: a朋友圈-style social app. Two packages in one repo (not a monorepo workspace):

- `backend/` — Python 3.12 + FastAPI + SQLAlchemy 2.x, managed with **uv** (not pip). `backend/app/` is the app; `backend/alembic/` migrations; `backend/tests/` pytest suite. Run backend commands with `cd backend && uv run ...`.
- `frontend/` — React 18 + TS + Vite. `@/*` path alias → `frontend/src`. State via Zustand stores in `frontend/src/stores/`. Build = `tsc -b && vite build`.

Backend serves the built frontend (`frontend/dist`) in production; dev runs them separately.

### Commands

Dev (both servers, Ctrl+C exits both): `bash scripts/dev.sh` — backend http://localhost:8000, frontend http://localhost:5173 (Vite proxies `/api` → backend; port via `VITE_BACKEND_PORT`).

Build frontend: `bash scripts/build.sh`.

Backend lint/format/typecheck/test (run in `backend/`):
- `uv run ruff check app && uv run ruff format --check app && uv run ruff format --check alembic`
- `uv run mypy app`
- `uv run pytest` (tests set `SKIP_ALEMBIC=1` and use a tmp SQLite DB; no external services needed)
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
- **Video handling needs ffmpeg/ffprobe** on PATH (`app/storage/filekit.py` validates videos with `ffprobe`). The Docker image installs `ffmpeg`; local dev must have it too.
- Migrations use `render_as_batch=True` (SQLite-friendly). SQLite enforces `PRAGMA foreign_keys=ON` in `app/database.py` and test conftest.
- Config is `pydantic-settings` (`app.config.Settings`); `settings` is a module-level singleton but tests/`lifespan` reassign it via `cfg.settings = cfg._create_settings()` after env changes — mutate env then re-create settings rather than editing the singleton.

### Frontend gotchas

- **`animal-island-ui` is loaded via CDN** in `frontend/index.html` (jsDelivr UMD script + CSS), not bundled, despite being a `package.json` dependency. Imports like `import { Card } from "animal-island-ui"` resolve to the global at runtime. When building UI in this repo, load the `animal-island-ui-style` skill for its conventions.
- Passwords are RSA-encrypted client-side before sending (`frontend/src/utils/rsa.ts` + `jsencrypt`); backend decrypts with `app/services/rsa_service.py` (key pair warmed up at startup via `_warmup_rsa`). Don't send plaintext passwords.
- Vite dev server proxies `/api` → `http://localhost:${VITE_BACKEND_PORT}` (default 8000).

### Env

`.env` is gitignored and mostly self-bootstrapping; see `.env.example` for the full list. Notable: `DEBUG`, `SECURE_COOKIES`, `DB_URL` (default `sqlite:///data/app.db`), `JWT_SECRET` (auto-generated if empty), `CORS_ORIGINS` (comma-separated, empty = no CORS), `STORAGE_ROOT`, media size limits, `PUBLIC_BASE_URL` (used for invite links).

### Layout notes

- `storage/` — runtime media files (gitignored). `data/` — SQLite DB (gitignored). `logs/` — runtime logs (gitignored). `docs/` — design docs (Chinese): `项目实现方案.md` is the detailed spec.
- API routes mounted under `/api`; docs at `/api/docs`, OpenAPI at `/api/openapi.json`.
- App layers: `app/api/` (routers), `app/services/` (business logic), `app/models/` (ORM), `app/schemas/` (Pydantic), `app/storage/` (media/ffprobe/filekit), `app/tasks/`, `app/core/`, `app/utils/`.
- `system_status` table holds the single init/admin row; `_ensure_system_status()` in `main.py` inserts the seed row idempotently at startup.

## tools
###  CodeGraph

Reach for CodeGraph BEFORE grep/find or reading files when you need to understand or locate code (requires a `.codegraph/` directory at the repo root).

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.

## 代码修改工作流规范

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
