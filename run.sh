#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

(cd frontend && npm run build)

export PYTHONPATH="$PWD"

# Stop any previous instance listening on port 8000
existing_pids=$(lsof -ti tcp:8000 -sTCP:LISTEN || true)
if [[ -n "$existing_pids" ]]; then
  echo "Stopping existing process on port 8000 (PID: $existing_pids)..."
  kill $existing_pids 2>/dev/null || true
  sleep 0.5
fi

echo "Starting English Notes Coach at http://127.0.0.1:8000"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
