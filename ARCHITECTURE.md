# EchoHelp Architecture

EchoHelp is an organizational memory engine for support/eng/ops teams.

North star: every system should serve at least one of:
- Retrieve memory
- Create memory
- Improve memory quality

This document is the “new engineer first read” overview.

## System overview

EchoHelp is a small web app with:
- A FastAPI backend (`backend/app/`)
- A React+TypeScript frontend (`frontend/`)
- A SQLite database (default `echohelp.db`, configurable via `ECHOHELP_DB_PATH`)

At a high level:
- Tickets are the primary “memory objects”.
- Feedback and logs are “memory quality signals”.
- Insights endpoints aggregate signals into cheap, factual summaries.

## Core flows

### 1) Search (retrieve memory)

**User goal**: find relevant historical tickets quickly.

**Frontend**
- `frontend/src/Search.tsx`
  - Keyword search: `/api/search`
  - Semantic search: `/api/semantic-search`
  - Renders results and a ticket inspector.

**Backend**
- Keyword search routes live under `backend/app/api/`.
- Semantic search uses embeddings stored in `embedding`.

**Data & invariants**
- Tickets should have stable identifiers.
- Embeddings should exist for tickets used in semantic search.

### 2) Ingest (create memory)

**User goal**: turn a thread/conversation into a ticket and make it searchable.

**Backend**
- Endpoint: `POST /api/ingest/thread`
- Service: `backend/app/services/ingest.py::ingest_thread`

**Idempotency contract**
- Re-ingesting the same `external_id` updates the existing ticket instead of creating a duplicate.
- Embeddings are created once per ticket (no duplicates).
- If the ingested thread is resolved, EchoHelp records a single “resolved via ingest” feedback event.

### 3) Ask Echo (retrieve + improve memory quality)

**User goal**: ask a question and get an answer grounded in system memory.

**Frontend**
- `frontend/src/AskEchoWidget.tsx`

**Backend**
- Endpoint: `POST /api/ask-echo`
- Every call creates an `AskEchoLog` row.

**Design stance**
- Answers must be auditable.
- Logged reasoning and references are treated as first-class data.

### 4) Feedback loop (improve memory quality)

**User goal**: capture what actually worked so future retrieval improves.

**Backend**
- Ticket feedback: `/api/ticket-feedback/`
- Ask Echo / snippet feedback routes exist for capturing helpful/not helpful signals.

**Data**
- `TicketFeedback` rows are the primary “did this help?” signal.

### 5) Insights / Pattern Radar (improve memory quality)

EchoHelp intentionally exposes multiple pattern surfaces so we don’t mix concerns.

#### Snippet Pattern Radar (KB performance)
- Endpoint: `GET /api/insights/pattern-radar`
- Purpose: how well the snippet/KB layer is performing.

#### Ticket Pattern Radar (queue themes)
- Endpoint: `GET /api/insights/ticket-pattern-radar?days=14`
- Purpose: what the ticket queue is telling us right now.

#### Feedback Patterns (user sentiment)
- Endpoint: `GET /api/patterns/summary?days=30`
- Purpose: simple, factual counts of positive/negative feedback.

## Contracts and versioning

Public JSON responses should include:

```json
{
  "meta": { "kind": "...", "version": "v1" }
}
```

Rules:
- Additive changes are preferred (new keys, don’t remove old keys).
- When a contract must change materially, introduce a new versioned endpoint.

## Testing and determinism

- Tests run with a per-test isolated SQLite DB (`tests/conftest.py`).
- Avoid hidden reliance on shared DB state or implicit ordering.

## Further detail

More detailed notes and endpoint-level discussion live in `docs/ARCHITECTURE.md`.
