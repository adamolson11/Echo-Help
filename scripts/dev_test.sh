#!/bin/bash
# EchoHelp API Endpoint Battery Test

set -euo pipefail

API_URL="http://localhost:8000/api"

function assert_grep() {
  local value="$1"
  local pattern="$2"
  local label="$3"
  echo "$value" | grep "$pattern" >/dev/null && echo "[PASS] $label" || { echo "[FAIL] $label: $value (expected: $pattern)"; exit 1; }
}

# 1. Health check
HEALTH=$(curl -sf "$API_URL/health")
assert_grep "$HEALTH" '"status":"ok"' "/health returns status ok"

# 2. Tickets should be empty
EMPTY_RESPONSE=$(curl -sf "$API_URL/tickets")
assert_grep "$EMPTY_RESPONSE" '\[\]' "/tickets is empty"

# 3. Seed demo tickets
SEED_RESPONSE=$(curl -sf -X POST "$API_URL/tickets/seed-demo")
assert_grep "$SEED_RESPONSE" 'seeded\|already exist' "/tickets/seed-demo works"

# 4. Tickets should now have data

# 5. Search endpoint
echo "5) Testing search endpoint..."
SEARCH_RESPONSE=$(curl -sf "$API_URL/search?q=login")
assert_grep "$SEARCH_RESPONSE" 'external_key' "/search returns matching tickets"

DEMO_RESPONSE=$(curl -sf "$API_URL/tickets")
assert_grep "$DEMO_RESPONSE" 'external_key' "/tickets returns demo data"

echo "\nAll API tests passed!"
