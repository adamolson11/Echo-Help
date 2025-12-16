#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../backend"
echo "[DEV] Starting backend on http://localhost:8001 ..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
