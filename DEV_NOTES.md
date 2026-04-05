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

## 2026-04-03 environment reconciliation

STATE:
- Active branch truth is a manual ticket-creation lane plus existing ingest and semantic features.
- The ingest readability checkpoint described in chat is not the only live workspace change on this branch.
- Team-wide reproducibility was not stable at the start of this pass because local/container runtimes were not using the same installed dependency set.

CHANGED:
- `backend/app/api/semantic_clusters.py` now degrades cleanly when `numpy` is absent instead of failing backend import at startup.
- `scripts/dev_check.sh` now verifies importable Python modules, not just binary presence, so missing `sqlmodel`/`fastapi` is caught before launch.
- This note is the shared source of truth for the current repair pass.

EVIDENCE:
- Branch diff truth inspected from workspace changes: ticket creation flow is present in `backend/app/api/tickets.py`, `backend/app/schemas/tickets.py`, `frontend/src/components/TicketCreateForm.tsx`, `frontend/src/pages/IntakePage.tsx`, and `tests/test_ticket_create_api.py`.
- Local/container mismatch evidence from this pass:
	- `PYTHONPATH=. /usr/bin/python3 -m scripts.demo_echohelp` failed when backend was unreachable.
	- `PYTHONPATH=. /usr/bin/python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001` initially failed with missing `uvicorn`, then with missing `numpy`.
	- Separate remote-run evidence reported `ModuleNotFoundError: No module named 'sqlmodel'` for `PYTHONPATH=. python -m scripts.ingest_sample_thread`.
- Verified after environment repair in this workspace:
	- `cd frontend && npm run build` passed.
	- `PYTHONPATH=. /usr/bin/python3 -m pytest -q tests/test_ticket_create_api.py tests/test_ingest_thread.py` passed.

ROOT CAUSE:
- The repo declares `sqlmodel` and core backend packages, but some operators/runners are invoking scripts without first installing the declared backend requirements.
- Backend startup imported semantic clustering eagerly, which created a hard dependency on `numpy` even for narrow lanes that do not use semantic clustering.
- CI and Docker install dependencies explicitly; ad hoc local/remote runs were relying on ambient environment state.

REQUIRED DEPS:
- For `PYTHONPATH=. python -m scripts.ingest_sample_thread`:
	- `sqlmodel`
	- `sqlalchemy`
	- `pydantic` (via FastAPI/SQLModel dependency tree)
- For targeted backend tests (`tests/test_ticket_create_api.py`, `tests/test_ingest_thread.py`):
	- `fastapi`
	- `sqlmodel`
	- `sqlalchemy`
	- `httpx`
	- `pytest`
- For backend startup (`uvicorn backend.app.main:app`):
	- `fastapi`
	- `sqlmodel`
	- `sqlalchemy`
	- `uvicorn`

OPTIONAL DEPS:
- `numpy`: required for semantic clustering and some vector math paths, but no longer required just to import and start the backend.
- `sentence-transformers`, `transformers`, `huggingface_hub`, `tokenizers`: required for transformer-backed embeddings; without them, embeddings degrade to fallback mode as designed.
- `scikit-learn`: optional for some clustering paths; endpoints degrade when unavailable.

LIVE DIFF TRUTH:
- Current workspace truth does not match a readability-only summary.
- The visible branch contains active manual ticket creation changes plus environment fragility around startup and dependency installation.

CI/CONTAINER GAP:
- CI installs backend dependencies explicitly with `pip install -r backend/requirements.txt` and separately installs `ruff pyright pytest`.
- The backend Docker image installs from the same root requirements via `backend/requirements.txt -> ../requirements.txt`.
- Remote/manual runners that skip the install step can fail immediately with missing `sqlmodel`, `uvicorn`, or `numpy`.

VERIFY COMMANDS:
- Minimum backend install: `python -m pip install -r backend/requirements.txt`
- Targeted backend validation: `PYTHONPATH=. python -m pytest -q tests/test_ticket_create_api.py tests/test_ingest_thread.py`
- Backend startup check: `PYTHONPATH=. python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001`
- Ingest script check: `PYTHONPATH=. python -m scripts.ingest_sample_thread`
- Frontend build check: `cd frontend && npm run build`
- Guardrail preflight: `bash scripts/dev_check.sh`

PR GUARD RECOMMENDATION:
- Require every status claim to pair a command with its result and the exact files inspected.
- Treat `bash scripts/dev_check.sh` plus one targeted pytest command as the minimum pre-review backend parity check.

NEXT SAFE MERGE STEP:
- Merge only after one operator validates the above commands in a clean environment that has first run `python -m pip install -r backend/requirements.txt` and records the results in the PR.
