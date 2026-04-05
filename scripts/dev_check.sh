#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")/.."

echo "[INFO] Installing locked backend requirements..."
python -m pip install -r backend/requirements.txt

echo "[INFO] Running prototype ingest sample..."
PYTHONPATH=. python -m scripts.ingest_sample_thread

echo "[INFO] Running prototype ingest tests..."
pytest -q tests/test_ingest_thread.py

if lsof -i :8000 &>/dev/null; then
  PID=$(lsof -t -i :8000)
  echo "[WARN] Port 8000 in use by PID $PID. Stopping..."
  kill -TERM "$PID"
  sleep 2
  if kill -0 "$PID" 2>/dev/null; then
    echo "[WARN] PID $PID did not stop after SIGTERM. Forcing shutdown..."
    kill -9 "$PID"
    sleep 1
  fi
fi

echo "[INFO] Locked prototype contract passed. Launching FastAPI server on port 8000..."
exec env PYTHONPATH="$PWD" python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
