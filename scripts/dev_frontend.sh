#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../frontend"
echo "[DEV] Starting Vite frontend on http://localhost:5174 ..."
npm run dev -- --port 5174
