#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://e.cps.vin}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

exec python -m uvicorn app.main:app --host "${HOST}" --port "${PORT}"
