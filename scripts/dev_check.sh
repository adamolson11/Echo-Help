#!/bin/bash
# EchoHelp Dev Environment Check & Server Launcher

set -e

cd "$(dirname "$0")/.."  # Go to repo root

# 1. Check Python and Uvicorn
PYTHON_PATH=$(which python || true)
UVICORN_PATH=$(which uvicorn || true)

if [[ -z "$PYTHON_PATH" || -z "$UVICORN_PATH" ]]; then
  echo "[ERROR] Python or Uvicorn not found in environment."
  exit 1
fi

echo "[OK] Python: $PYTHON_PATH"
echo "[OK] Uvicorn: $UVICORN_PATH"

# 2. Check port 8000
if lsof -i :8000 &>/dev/null; then
  PID=$(lsof -t -i :8000)
  echo "[WARN] Port 8000 in use by PID $PID. Killing..."
  kill -9 $PID
  sleep 1
fi

echo "[OK] Port 8000 is free."

# 3. Start backend server (no reload for max compatibility)
echo "[INFO] Launching FastAPI server on port 8000..."
PYTHONPATH="$PWD" uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
