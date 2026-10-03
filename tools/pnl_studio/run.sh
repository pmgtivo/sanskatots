#!/usr/bin/env bash
# Start PnL Studio: sets up the venv if needed, installs deps once, opens the browser.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
VENV="$REPO_ROOT/.venv"
PORT="${PNL_PORT:-8777}"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Creating virtualenv at $VENV"
  python3 -m venv "$VENV"
fi
PY="$VENV/bin/python"

if ! "$PY" -c 'import fastapi, uvicorn, multipart, pandas, openpyxl' >/dev/null 2>&1; then
  echo "Installing PnL Studio dependencies..."
  "$PY" -m pip install --quiet --upgrade pip
  "$PY" -m pip install --quiet -r "$HERE/requirements.txt"
fi

URL="http://127.0.0.1:$PORT"
if [[ "${PNL_NO_BROWSER:-}" != "1" ]]; then
  ( sleep 2; command -v open >/dev/null && open "$URL" ) &
fi

echo "PnL Studio -> $URL   (Ctrl-C to stop)"
cd "$HERE"
exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" ${PNL_RELOAD:+--reload}
