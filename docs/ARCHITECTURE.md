# Echo-Help Architecture Overview

## High-Level Domains

- **Ticket Search**: Keyword and semantic search over historical tickets.
- **Ask Echo**: AI assistant that answers natural-language questions using tickets and snippets.
- **Snippet Library**: Reusable solution snippets distilled from ticket feedback.
- **Ask Echo Logs**: Auditable history of Ask Echo questions, answers, and reasoning.

## Data Flows

### Ticket Search

1. User types a query and chooses keyword or AI search in `Search.tsx`.
2. Frontend calls either `/api/search` (keyword) or `/api/semantic-search`.
3. Backend routes hit the DB and/or embedding index to return matching tickets.
4. `Search.tsx` renders results and an inspector panel for the selected ticket.

### Ask Echo

1. User asks a natural-language question in `AskEchoWidget.tsx`.
2. Frontend POSTs to `/api/ask-echo` with `{ q, limit }`.
3. Backend `ask_echo.py`:
   - Runs semantic ticket search and snippet search.
   - Chooses an answer mode (`kb_answer` vs `general_answer`).
   - Builds an answer, references, snippet summaries, and a `reasoning` object.
   - Persists an `AskEchoLog` row including reasoning JSON.
4. Response is rendered by `AskEchoWidget`, including:
   - Answer text and mode.
   - Related tickets.
   - A collapsible "Why Echo chose this answer" panel.

### Snippet Library

1. Feedback from tickets and Ask Echo flows into `/api/snippets/feedback`.
2. Backend updates `SolutionSnippet` rows and recalculates `echo_score`.
3. `/api/snippets/search` exposes a text search over snippets.
4. `Search.tsx` KB tab calls `/api/snippets/search` and renders snippet cards.

### Ask Echo Logs (Audit)

1. Every Ask Echo call logs an `AskEchoLog` row with:
   - Query, scores, mode, reference counts.
   - Reasoning JSON for candidate and chosen snippets.
2. `/api/ask-echo/logs` returns recent summaries for Insights.
3. `/api/ask-echo/logs/{id}` returns full detail including reasoning JSON.
4. `AskEchoLogsPanel.tsx` shows a table of logs and a detail view with reasoning.

## Backend Structure

- `backend/app/api/routes/search.py` – Ticket search endpoints.
- `backend/app/api/routes/semantic_search.py` – Semantic search endpoints.
- `backend/app/api/routes/ask_echo.py` – Ask Echo query, reasoning, and logs endpoints.
- `backend/app/api/routes/snippets.py` – Snippet create, feedback, and search.
- `backend/app/api/routes/insights.py` – Insights and feedback aggregations.
- `backend/app/models/` – SQLModel models for tickets, snippets, feedback, AskEchoLog.
- `backend/app/services/` – Search and snippet processing helpers.

## Frontend Structure

- `frontend/src/Search.tsx` – Main ticket search UI, filters, tabs (search/insights/kb), and inline Ask Echo card.
- `frontend/src/AskEchoWidget.tsx` – Ask Echo input, answer view, feedback, and reasoning panel.
- `frontend/src/AskEchoLogsPanel.tsx` – Insights panel to review Ask Echo logs and reasoning.
- `frontend/src/components/SnippetCard.tsx` – Reusable snippet display for the KB tab.
- `frontend/src/components/TicketResultCard.tsx` – Reusable ticket result row/card for search results.

## Embeddings and Semantic Search

- Text embeddings are generated for tickets (and possibly snippets) during ingestion.
- Semantic search endpoints use these embeddings to find similar tickets.
- Ask Echo uses semantic search to ground answers and drive the reasoning data it logs.

## Pattern & Insights Endpoints

Echo exposes three orthogonal “pattern” surfaces. They answer different questions and are designed to evolve independently.

### 1. Snippet Pattern Radar (KB performance)

**Endpoint**

- `GET /api/insights/pattern-radar`

**Question it answers**

> "How well is our knowledge base / snippet layer performing?"

**Response shape (v1)**

- `stats.total_snippets` – number of snippets in the radar window.
- `stats.total_successes` – how often snippets were marked as successful.
- `stats.total_failures` – how often snippets were associated with failed resolutions.
- `top_frequent_snippets` – snippets ranked by total uses.
- `top_risky_snippets` – snippets ranked by failures.
- `meta`:
   - `kind: "snippet"`
   - `version: "v1"`

Design stance: **stable / legacy-friendly**. This is the v1 contract for snippet radar; new behavior should be added additively or via a new versioned endpoint.

### 2. Ticket Pattern Radar (queue themes)

**Endpoint**

- `GET /api/insights/ticket-pattern-radar?days=14`

**Question it answers**

> "What is the ticket queue trying to tell us right now?"

**Response shape (v1)**

- `top_keywords: { keyword: string; count: number }[]` – word-level patterns across ticket text fields.
- `frequent_titles: { title: string; count: number }[]` – recurring ticket titles/summaries.
- `semantic_clusters: []` – reserved for future semantic grouping (currently placeholder).
- `stats`:
   - `total_tickets` – tickets considered in the window.
   - `window_days` – the size of the time window (e.g. 7, 14, 30).
- `meta`:
   - `kind: "ticket"`
   - `version: "v1"`

Design stance: **primary growth surface** for Pattern Radar. We can add fields (e.g., clusters, per-queue breakdowns) as long as existing keys remain stable.

### 3. Feedback Pattern Summary (user sentiment about Echo)

**Endpoint**

- `GET /api/patterns/summary`

**Question it answers**

> "What are users telling us about Echo’s answers?"

This surface focuses on Ask Echo feedback and related signals (e.g., thumbs up/down, free-text comments). It is intentionally **kept separate** from ticket and snippet radar so we don’t mix “what the queue is doing” with “how Echo is perceived” in a single response blob.

### Versioning & evolution

- New dimensions should be added:
   - As new top-level keys on existing endpoints, **or**
   - As new sibling endpoints (e.g., `/api/insights/ticket-pattern-radar/clusters`) when payloads become large/expensive.
- Existing keys (`stats`, `top_keywords`, `frequent_titles`, etc.) should not be removed or renamed without introducing a clearly versioned alternative (e.g., `/ticket-pattern-radar-v2`).

