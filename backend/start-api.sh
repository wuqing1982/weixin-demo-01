#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-http://localhost:8000}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
PYTHON_BIN="../.venv/bin/python"

if [ ! -x "${PYTHON_BIN}" ]; then
    PYTHON_BIN="python3"
fi

exec "${PYTHON_BIN}" -m uvicorn app.main:app --host "${HOST}" --port "${PORT}"
