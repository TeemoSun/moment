# AGENTS.md

Guidance for AI agents working in this repo. High-signal, repo-specific facts only.

## Stack

- Monorepo: `backend/` (FastAPI + SQLAlchemy 2.0 async + SQLite, uv-managed) + `frontend/` (Vite + React 19 + TypeScript + TanStack Query + Tailwind).
- Frontend UI: Apple HIG-style design via `liquidify-react` (Button/Card/Badge/IconButton/Icon/ThemeProvider) + `lucide-react` icons + `framer-motion` (peer deps). Tailwind utility classes remain for layout; Apple-style form controls use `.glass`/`.glass-input` component classes in `src/index.css`.
- Single-service architecture: FastAPI serves the built frontend as static assets from `backend/app/static/`. Not a separate frontend server in production.
- All mutable data lives under `data/` (gitignored): `db/`, `uploads/`, `logs/`, `ssl/`. SQLite DB at `data/db/moment.sqlite3`.

## Commands

### Full app (HTTPS on :8443)
```bash
cp .env.example .env && echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env
bash scripts/start.sh          # builds frontend if static missing, uv sync, starts uvicorn over HTTPS
```

### Dev mode (hot reload, frontend separate)
```bash
# Backend (note: port 18443, NOT 8443)
cd backend && JWT_SECRET=dev-secret uv run uvicorn app.main:app --reload --port 18443
# Frontend (Vite proxies /api -> http://127.0.0.1:18443, see vite.config.ts)
cd frontend && npm run dev
```

### Build / lint / test
```bash
# Frontend
cd frontend && npm ci
npm run build        # = sync:liquidify + tsc -b && vite build; output copied to backend/app/static by scripts/build.sh
npm run lint         # oxlint (NOT eslint). No standalone typecheck script; run `npx tsc -b` to typecheck.

# Backend
cd backend && uv sync                       # dev deps
cd backend && uv sync --no-dev --frozen     # prod (matches Dockerfile)
cd backend && uv run pytest                 # pytest-asyncio, asyncio_mode=auto; tests/ is currently empty
cd backend && uv run pytest tests/foo.py -k name   # single test (none exist yet)
```

## Gotchas

- **`JWT_SECRET` is required** (≥16 chars) or the app fails to start. `Settings._secret_required` validates this. For dev, pass `JWT_SECRET=dev-secret`.
- **Alembic is NOT wired up.** It's a dependency and `backend/alembic/versions/` exists, but there is no `alembic.ini` or `env.py`. Schema is created via `Base.metadata.create_all` in `app.database.init_db()` on startup. Do not look for `alembic upgrade`/migration commands.
- **New ORM models must be registered**: `init_db()` does `import app.models` so models are picked up by `Base.metadata`. If you add a model file, ensure it's imported there or by `app/models/__init__.py`.
- **`backend/app/static/` is a build artifact** (gitignored), produced by `scripts/build.sh` (builds frontend, copies `dist/` → `backend/app/static/`). `start.sh` auto-builds it if missing; force rebuild with `FORCE_BUILD=1 bash scripts/start.sh`.
- **`liquidify-react/styles` CSS import conflicts with Tailwind's PostCSS** (its `@layer base` declarations trigger `CssSyntaxError` during `vite build`). Do NOT use `import 'liquidify-react/styles'` in TS. Instead, the CSS is copied to `public/liquidify.css` via `npm run sync:liquidify` (runs automatically before `dev`/`build`) and loaded via a `<link>` tag in `index.html`. The copy in `public/` is committed; re-run the sync script after bumping `liquidify-react`.
- **SPA routing**: `/api/*` returns a strict 404 (never falls back to `index.html`); all other unknown paths serve `index.html`. See `app/main.py` `spa_fallback`.
- **Dev port is 18443**, production is 8443. The Vite dev server proxies `/api` to `127.0.0.1:18443` — keep these in sync if you change the dev port.
- **Self-signed TLS certs** are auto-generated into `data/ssl/` on startup if `SSL_CERT_FILE`/`SSL_KEY_FILE` are unset (see `app/ssl_gen.py`). Set both env vars to use real certs.
- **Registration is invite-code-gated.** First run needs a manually seeded admin + invite code (script in README.md "创建管理员与邀请码"); without it no one can register.

## Conventions

- Backend: `from __future__ import annotations` at top of modules; SQLAlchemy 2.0 `Mapped`/`mapped_column` style; UUID-string primary keys.
- Routers in `app/routers/` (auth, users, friends, media, posts, comments, admin); business logic in `app/services/`; cross-cutting in `app/core/` (file validation, thumbnails, rate limiting, permissions).
- Auth: JWT access token (Bearer header) + refresh token (httpOnly cookie). Dependencies: `get_current_user`, `get_admin_user` in `app/deps.py`.
- Frontend path alias: `@` → `src/` (tsconfig + vite). Linter is `oxlint`.
- No CI, no pre-commit hooks configured.