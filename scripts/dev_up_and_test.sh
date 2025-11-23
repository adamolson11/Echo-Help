#!/bin/bash
# Start backend server in background, wait, then run API tests
set -euo pipefail

cd "$(dirname "$0")/.."

# Start backend server in background
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
cd ..

# Wait for server to be up
for i in {1..10}; do
  if curl -sf http://localhost:8000/api/health >/dev/null; then
    echo "[OK] Backend server is up."
    break
  fi
  echo "[INFO] Waiting for backend to start... ($i)"
  sleep 1
done

if ! curl -sf http://localhost:8000/api/health >/dev/null; then
  echo "[FAIL] Backend server did not start in time."
  kill $SERVER_PID || true
  exit 1
fi

# Run tests
./scripts/dev_test.sh
TEST_EXIT=$?

# Kill backend server
kill $SERVER_PID || true

exit $TEST_EXIT
