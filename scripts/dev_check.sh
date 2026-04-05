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
  kill "$PID"
  sleep 1
fi

echo "[INFO] Locked prototype contract passed. Launching FastAPI server on port 8000..."
exec env PYTHONPATH="$PWD" python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
