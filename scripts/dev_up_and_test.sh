#!/bin/bash
# Start backend server in background, wait, then run API tests
set -euo pipefail

cd "$(dirname "$0")/.."

# Start backend server in background
PYTHONPATH="$PWD" uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 &
SERVER_PID=$!

# Wait for server to be up
for i in {1..10}; do
  if curl -sf http://localhost:8001/api/health >/dev/null; then
    echo "[OK] Backend server is up."
    break
  fi
  echo "[INFO] Waiting for backend to start... ($i)"
  sleep 1
done

if ! curl -sf http://localhost:8001/api/health >/dev/null; then
  echo "[FAIL] Backend server did not start in time."
  kill $SERVER_PID || true
  exit 1
fi


# Seed demo tickets
echo "[INFO] Seeding demo tickets..."
curl -sf -X POST http://localhost:8001/api/tickets/seed-demo || true

# Backfill embeddings
echo "[INFO] Backfilling ticket embeddings..."
python3 -m scripts.backfill_embeddings

# Test /api/intake
INT_RESPONSE=$(curl -s -X POST http://localhost:8001/api/intake \
  -H "Content-Type: application/json" \
  -d '{"text":"user cannot login"}')
echo "$INT_RESPONSE" | grep "suggested_tickets" >/dev/null

# Run tests
./scripts/dev_test.sh
TEST_EXIT=$?

# Kill backend server
kill $SERVER_PID || true

exit $TEST_EXIT
