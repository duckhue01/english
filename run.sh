#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d frontend/dist ]]; then
  (cd frontend && npm run build)
fi

export PYTHONPATH="$PWD/backend"
echo "Starting English Notes Coach at http://127.0.0.1:8000"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
