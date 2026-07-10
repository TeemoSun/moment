#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

echo ">> Building frontend..."
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install
fi
npm run build

echo ">> Copying build output to backend/app/static..."
rm -rf "$ROOT/backend/app/static"
cp -r dist "$ROOT/backend/app/static"
echo ">> Done."