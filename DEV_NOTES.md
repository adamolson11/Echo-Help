# EchoHelp Dev Notes

This document captures intentional tradeoffs, known rough edges, and “not yet” decisions.

## Current priorities

Phase 1 (foundation hardening):
- Deterministic tests (no shared DB leakage)
- Explicit, versioned response contracts
- Idempotent ingest + predictable feedback behavior
- Defensive frontend rendering (fail soft)

## Known tradeoffs (intentional)

- **SQLite-first**: We use SQLite for local dev and tests. The DB path is configurable via `ECHOHELP_DB_PATH`.
- **Cheap insights**: v1 insights are designed to be inexpensive and easy to reason about. We prefer counts and simple aggregations over “smart” inference.
- **Additive evolution**: API responses should evolve additively. If we need breaking changes, we create a new versioned endpoint.

## Contracts

Guideline: “public” JSON responses should include:

```json
{ "meta": { "kind": "...", "version": "v1" } }
```

If a response is intentionally a bare list for convenience, it should be treated as legacy and migrated to an envelope (`{meta, items}`) when touching it.

## Testing notes

- Tests run against a per-test isolated temp SQLite DB via `tests/conftest.py`.
- Avoid module-import-time `os.environ["ECHOHELP_DB_PATH"] = ...` patterns.

## Frontend notes

Frontend refactor freeze (Phase 1):
- No UX reworks, component reshuffles, or visual polish.
- Only touch frontend when contracts/types break or to fix correctness/errors.

- Defensive rendering is required: never call `.map`/`.filter` on values that may be `undefined`.
- Prefer explicit normalization of backend responses at fetch boundaries.

## Ingest idempotency

`POST /api/ingest/thread` is designed to be idempotent by `external_id`:
- Re-ingesting the same `external_id` updates the existing ticket.
- Embeddings are created once per ticket.
- Resolved threads create at most one “resolved via ingest” feedback row.

## Embeddings disabled mode

- Embeddings may be disabled if `sentence_transformers` is missing or `ECHO_EMBEDDINGS=off`.
- When disabled, deterministic fallback embeddings are stored (dim=8).
- If ML embeddings are later enabled (e.g., 384-d), prior fallback vectors will not match dims
	and will be skipped in semantic search.
- Mitigation: re-embed or re-ingest tickets once ML deps are installed.

## Deprecation warnings

You may see warnings about `datetime.utcnow()` deprecation. We’ll migrate to timezone-aware timestamps (`datetime.now(datetime.UTC)`) in a targeted pass once Phase 1 stability gates are fully satisfied.

## Not yet (explicit)

We are intentionally not building (for now):
- A ticketing system replacement
- Multi-agent orchestration
- Auto-remediation
- Predictive ML beyond basic aggregation

If a feature request drifts into these areas, pause and reassess against the product north star.

## 2026-02-25 post-merge stabilization

- Merge commit on `main`: `52d11a3` (merged `fix/ask-echo-error-handling`).
- Ask Echo frontend error handling improvements:
	- Classified error UX for offline/network, HTTP 5xx, and HTTP 4xx.
	- Retry action and optional details panel in response area.
	- Defensive fallback when no response payload is returned.
- Current ML fallback state:
	- `sentence_transformers` is not installed in this environment.
	- Embeddings run in fallback mode (deterministic, low-dim vectors) with semantic search degradation expected.
- Known limitations:
	- Browser console errors were not fully programmatically harvested in this pass; runtime API and UI route smoke checks were used for validation.

## Ask Echo Demo Stability - Definition of Done

DONE means all criteria are true:
1. If backend returns non-200 or network fails, UI shows a friendly error and does not crash.
2. If backend returns empty/invalid payload, UI shows fallback message and does not crash.
3. While request is in-flight, submit is disabled and a loading state is visible.
4. Frontend build passes with `npm run build`.

### Anti-theater check (2026-02-25)

- Acceptance status:
	1. PASS
	2. PASS
	3. PASS
	4. PASS
- Automated artifact added: backend failure-schema coverage for `POST /api/ask-echo` invalid query.
- Test command: `pytest -q tests/test_ask_echo.py`
- Build command (frontend criterion): `cd frontend && npm run build`

## 2026-02-26 big seed corpus + bad-aware retrieval

Generate dataset (JSONL):
- `python -m backend.scripts.generate_seed_tickets --count 600 --out backend/app/seed_data/tickets_big_seed.jsonl`

Seed dataset:
- Dry run + histogram only: `python -m backend.scripts.seed_tickets --path backend/app/seed_data/tickets_big_seed.jsonl --dry-run`
- Idempotent reset + insert: `python -m backend.scripts.seed_tickets --path backend/app/seed_data/tickets_big_seed.jsonl --reset`

Bad-aware retrieval (deterministic):
- Ask Echo ranking applies a penalty when `answer_quality_label == "bad"` and applies a boost when `fix_confirmed_good == true`.
- Signal fields are surfaced as evidence metadata (`answer_quality_label`, `boosts_applied`, and `final_score`) so ranking behavior is explainable and testable.

Targeted tests:
- `pytest -q tests/test_seed_tickets.py tests/test_ranking_policy_learning_lite.py`

Deferred diagnostics (non-blocking):
- Editor import-resolution warnings for `sqlmodel`/`backend.*` in new script files are environment analysis warnings (not runtime failures); seeding commands and targeted pytest pass in the project runtime environment.
