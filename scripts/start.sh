#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Ensure uv is on PATH (common install locations)
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Auto-create .env with a generated JWT_SECRET if missing
if [ ! -f "$ROOT/.env" ]; then
  echo ">> No .env found, creating one with a generated JWT_SECRET..."
  cp "$ROOT/.env.example" "$ROOT/.env"
  SECRET=$(openssl rand -hex 32)
  if grep -q "^JWT_SECRET=" "$ROOT/.env"; then
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${SECRET}|" "$ROOT/.env"
  else
    echo "JWT_SECRET=${SECRET}" >> "$ROOT/.env"
  fi
fi

# load .env if present
if [ -f "$ROOT/.env" ]; then
  set -a; . "$ROOT/.env"; set +a
fi

# Verify JWT_SECRET is set
if [ -z "${JWT_SECRET:-}" ]; then
  echo "ERROR: JWT_SECRET is not set. Add it to .env" >&2
  exit 1
fi

export APP_ENV="${APP_ENV:-production}"
export APP_HOST="${APP_HOST:-0.0.0.0}"
export APP_PORT="${APP_PORT:-8443}"

echo "=== Moment startup ==="
echo "ENV=$APP_ENV  HOST=$APP_HOST  PORT=$APP_PORT"

# 1. Build frontend if static not present or forced
FORCE_BUILD="${FORCE_BUILD:-0}"
if [ ! -d "$ROOT/backend/app/static" ] || [ "$FORCE_BUILD" = "1" ]; then
  echo ">> Building frontend..."
  bash "$ROOT/scripts/build.sh"
fi

# 2. Install python deps
echo ">> Syncing python deps..."
cd "$ROOT/backend"
uv sync
cd "$ROOT"

# 3. Ensure data dirs
mkdir -p "$ROOT/data/db" "$ROOT/data/uploads" "$ROOT/data/logs" "$ROOT/data/ssl"

# 4. Start backend (HTTPS). Ctrl+C kills the whole process group.
echo ">> Starting backend on https://$APP_HOST:$APP_PORT"
trap 'echo; echo ">> Stopping all services..."; kill 0' INT TERM
uv run --directory "$ROOT/backend" uvicorn app.main:app \
  --host "$APP_HOST" --port "$APP_PORT" \
  --ssl-certfile "$ROOT/data/ssl/cert.pem" \
  --ssl-keyfile "$ROOT/data/ssl/key.pem" &

wait