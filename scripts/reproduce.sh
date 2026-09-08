#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="${PYTHONPATH:-}:$ROOT_DIR/src"
export OP06_ALLOW_DEMO_MODEL="${OP06_ALLOW_DEMO_MODEL:-1}"
PORT="${PORT:-8000}"

exec python3 -m uvicorn op06.api.app:app --host 0.0.0.0 --port "$PORT"