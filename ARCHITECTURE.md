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

## Canonical Events and Their Purpose

EchoHelp treats certain tables/endpoints as **canonical event producers**.
Downstream logic (Insights, ranking, “memory quality”) must consume these events
directly rather than inferring meaning from side effects.

Rules:
- Events are append-only “what happened” records.
- Avoid interpreting an event as something it doesn’t explicitly state.
- If a new meaning is required, add an explicit field or a new event type.

### 1) Ticket ingest

- **Emitted by**: `POST /api/ingest/thread` (and other ingest paths)
- **Represents**: A ticket (memory object) created or updated from an external source
- **Must never be inferred**:
  - “User tried the fix” (ingest does not imply resolution)
  - “This ticket helped” (helpfulness requires feedback events)
- **Why it exists**: Establishes system memory and stable identifiers

### 2) Ask Echo query

- **Emitted by**: `POST /api/ask-echo` → `AskEchoLog`
- **Represents**: A question asked + the system’s chosen answer mode and grounding
- **Must never be inferred**:
  - “The answer was correct” (requires feedback)
  - “A referenced ticket solved it” (requires ticket/snippet feedback)
- **Why it exists**: Auditable retrieval trace and the backbone of the feedback loop

### 3) Ask Echo feedback

- **Emitted by**: `POST /api/ask-echo/feedback` → `AskEchoFeedback`
- **Represents**: Answer-level signal for a specific `AskEchoLog`
- **Must never be inferred**:
  - “A specific ticket was helpful” (that’s ticket-level feedback)
  - “A specific snippet was helpful” (that’s snippet-level feedback)
- **Why it exists**: Measures answer quality even when ungrounded

### 4) Ticket feedback

- **Emitted by**: `POST /api/ticket-feedback/` → `TicketFeedback`
- **Represents**: A user signal that a ticket/solution helped or didn’t, plus optional resolution notes
- **Must never be inferred**:
  - “Echo suggested this ticket” (that association lives in AskEchoLog)
- **Why it exists**: Primary “what worked” memory-quality signal

### 5) Snippet feedback

- **Emitted by**: `POST /api/snippets/feedback` → `SnippetFeedback` (+ updates to `SolutionSnippet`)
- **Represents**: KB/snippet usefulness signal and optional notes
- **Must never be inferred**:
  - “Snippet equals a ticket resolution” (snippets are reusable and may generalize)
- **Why it exists**: Lets the KB layer improve without hidden heuristics

### 6) Tasks (planned)

- **Emitted by**: (not implemented yet)
- **Represents**: Explicit work items the system tracks (e.g., follow-ups, cleanups)
- **Must never be inferred**: “A task exists because a pattern exists”
- **Why it exists**: Future bridge between insights and actionable work, without magic

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
- Ask Echo feedback: `/api/ask-echo/feedback`
- Snippet feedback: `/api/snippets/feedback`

#### Feedback types (taxonomy)

EchoHelp intentionally captures multiple *complementary* feedback signals. These are not duplicates:

- **Answer-level feedback** (`AskEchoFeedback`, keyed by `ask_echo_log_id`)
  - Attaches to a specific Ask Echo answer/log.
  - Works even when the answer is **ungrounded** (no related ticket).
  - Primary use: evaluate answer quality and learn when/why grounding fails.

- **Ticket-level feedback** (`TicketFeedback`, keyed by `ticket_id`)
  - Captures whether a particular ticket/solution was useful and what actually resolved the issue.
  - Primary use: improve “memory quality” signals (counts, sentiment, and clustering).

- **Snippet-level feedback** (`SnippetFeedback`, keyed by `snippet_id` or `ticket_id`)
  - Captures whether a generated/curated snippet helped.
  - Primary use: tune KB snippet scoring (`echo_score`).

Rule of thumb:
- `ask_echo_log_id` answers “was this *answer* helpful?”
- `ticket_id` answers “was this *ticket* helpful?”
- `snippet_id` answers “was this *snippet* helpful?”

Note: `/api/feedback` exists as a small legacy wrapper used by Intake; it maps to `TicketFeedback`.

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
