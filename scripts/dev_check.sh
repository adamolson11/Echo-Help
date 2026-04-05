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

# 1b. Check importable runtime dependencies in the active Python environment.
PYTHONPATH="$PWD" "$PYTHON_PATH" <<'PY'
import importlib
import sys

required = ["fastapi", "sqlalchemy", "sqlmodel", "uvicorn"]
optional = ["numpy", "sentence_transformers", "sklearn"]

missing_required: list[str] = []

for name in required:
  try:
    importlib.import_module(name)
  except ModuleNotFoundError:
    missing_required.append(name)

if missing_required:
  print("[ERROR] Missing required Python modules:", ", ".join(missing_required))
  print("[ERROR] Install backend dependencies before launching the app.")
  print("[ERROR] Suggested command: python -m pip install -r backend/requirements.txt")
  sys.exit(1)

print("[OK] Required Python modules are importable.")

missing_optional: list[str] = []
for name in optional:
  try:
    importlib.import_module(name)
  except ModuleNotFoundError:
    missing_optional.append(name)

if missing_optional:
  print("[WARN] Optional ML modules missing:", ", ".join(missing_optional))
  print("[WARN] Semantic clustering / transformer-backed embeddings may degrade or disable.")
else:
  print("[OK] Optional ML modules are importable.")
PY

# 1c. Execute the locked prototype runtime contract.
echo "[INFO] Running prototype ingest contract..."
PYTHONPATH="$PWD" "$PYTHON_PATH" -m scripts.ingest_sample_thread

echo "[INFO] Running prototype ingest test..."
PYTHONPATH="$PWD" "$PYTHON_PATH" -m pytest -q tests/test_ingest_thread.py

echo "[OK] Prototype ingest contract passed."

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
