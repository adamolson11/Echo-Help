# EchoHelp Project State Audit

This document consolidates the two reconstruction attempts that were opened on
2026-03-16 and records the current, reviewable project state.

## Reconciled pull requests

### PR #2 — `copilot/vscode-mmt8528w-r8fy`
- **Intent:** repository survey plus CI/dependency repair.
- **Observed changes:** added `docs/ECHO_CORTEX_TRACE_SYSTEM_NORTH_STAR_v0.3.md`,
  added `backend/app/seed_data/drill_sessions.jsonl`, and rewrote
  `backend/app/seed_data/tickets_big_seed.jsonl`.
- **What was kept:** the useful finding that CI and local setup referenced
  `backend/requirements.txt`, but the file did not exist.
- **What was not kept:** the seed-data churn and north-star pseudo-code doc,
  because neither reflected the existing repository conventions or the current
  product state.

### PR #3 — `copilot/survey-current-repository-structure`
- **Intent:** produce a repository survey, architecture map, risk check, and
  next-step plan.
- **Observed changes:** no repository files changed.
- **What was kept:** the audit scope is captured here and mapped onto the
  current canonical docs.

## Current documentation baseline

- `ARCHITECTURE.md` — new engineer architecture overview and canonical system
  flows.
- `docs/ARCHITECTURE.md` — endpoint-level architecture details and response
  surface notes.
- `DEV_NOTES.md` — tradeoffs, stability notes, and known limitations.
- `IRON_OPERATING_FRAMEWORK.md` — contributor operating rules for constrained
  agent-driven edits.

## Repository overview

- `backend/` — FastAPI + SQLModel application, seed data, and backend scripts.
- `frontend/` — React + TypeScript UI built with Vite.
- `tests/` — pytest suite for API, ingest, Ask Echo, ranking, and insights.
- `scripts/` — local developer helpers for DB setup, demos, and validation.

## Development status

- Backend tests currently pass locally once Python dependencies are installed.
- Frontend production build currently passes once frontend dependencies are
  installed.
- Ruff and pyright still report pre-existing issues on `main`; those findings
  are outside the scope of this reconciliation pass.

## Risks to track

1. CI and local setup must share the same backend dependency manifest.
2. Semantic search can degrade gracefully when embeddings are unavailable, but
   model downloads still depend on external network access.
3. The repository has overlapping docs; reviewers should treat
   `ARCHITECTURE.md`, `docs/ARCHITECTURE.md`, and `DEV_NOTES.md` as the current
   canonical set.

## Safe next tasks

1. Resolve the existing ruff import-order findings.
2. Resolve the current pyright type errors on `main`.
3. Keep backend dependency declarations in one maintained path.
4. Decide whether the duplicate introductory block in `README.md` should be
   cleaned up in a separate documentation pass.
