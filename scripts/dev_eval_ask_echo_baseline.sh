#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

DAYS=90
LIMIT=5000
OUT="/tmp/ask_echo_training_export.json"
GRID_SEARCH=0
TICKET_THRESHOLD=0.6
SNIPPET_THRESHOLD=0.0

usage() {
  cat <<EOF
Usage: bash scripts/dev_eval_ask_echo_baseline.sh [options]

Exports Ask Echo labeled training rows from the local SQLite DB and evaluates
simple threshold baselines.

Options:
  --days N                 Lookback window (default: $DAYS)
  --limit N                Max rows (default: $LIMIT)
  --out PATH               Write export JSON to PATH (default: $OUT)
  --grid-search            Search thresholds that maximize F1
  --ticket-threshold X     Ticket score threshold (default: $TICKET_THRESHOLD)
  --snippet-threshold X    Snippet echo_score threshold (default: $SNIPPET_THRESHOLD)

Notes:
  - Uses ECHOHELP_DB_PATH if set; otherwise uses ./echohelp.db
  - Requires at least 1 Ask Echo feedback row to exist
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days)
      DAYS="$2"; shift 2;;
    --limit)
      LIMIT="$2"; shift 2;;
    --out)
      OUT="$2"; shift 2;;
    --grid-search)
      GRID_SEARCH=1; shift 1;;
    --ticket-threshold)
      TICKET_THRESHOLD="$2"; shift 2;;
    --snippet-threshold)
      SNIPPET_THRESHOLD="$2"; shift 2;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2;;
  esac
done

echo "[INFO] Exporting Ask Echo training data..."
PYTHONPATH=. python3 -m scripts.export_ask_echo_training_data --days "$DAYS" --limit "$LIMIT" > "$OUT"

COUNT=$(python3 - "$OUT" <<'PY'
import json
import sys
if len(sys.argv) < 2:
  raise SystemExit(2)
p = sys.argv[1]
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)
print(len(data) if isinstance(data, list) else 0)
PY
)

if [[ "$COUNT" -le 0 ]]; then
  echo "[WARN] Export contains 0 labeled rows: $OUT" >&2
  echo "[HINT] Generate some Ask Echo feedback in the UI (or via POST /api/ask-echo/feedback) and rerun." >&2
  exit 1
fi

echo "[OK] Exported $COUNT rows to $OUT"

eval_args=(--data "$OUT")
if [[ "$GRID_SEARCH" -eq 1 ]]; then
  eval_args+=(--grid-search)
else
  eval_args+=(--ticket-threshold "$TICKET_THRESHOLD" --snippet-threshold "$SNIPPET_THRESHOLD")
fi

echo "[INFO] Evaluating baseline..."
python3 scripts/eval_ask_echo_baseline.py "${eval_args[@]}"
