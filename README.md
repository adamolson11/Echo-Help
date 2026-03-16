# Echo-Help
A support tool fot CMS ticketing systems
EchoHelp
AI-Powered Support Intelligence & Living Knowledge System

MVP Scope • Private Repository (v0.1)

📌 Overview

EchoHelp is an AI-driven support intelligence platform that sits on top of existing ticketing and knowledge systems (e.g., Jira, Confluence).
It transforms how support teams search, categorize, resolve, and continually improve their documentation.

At its core, EchoHelp turns a single natural-language problem description into:

# EchoHelp

EchoHelp is a small SaaS-style tool for IT support teams.  
It lets agents search historical tickets, record what actually fixed each issue, and surface unresolved problem patterns over time — with optional **AI semantic search** powered by embeddings.

---

## 📚 Project documentation

- `docs/PROJECT_STATE_AUDIT.md` – reconstruction summary, retained/excluded PR
  work, and current follow-up risks.
- `ARCHITECTURE.md` – new engineer architecture overview and system contracts.
- `docs/ARCHITECTURE.md` – endpoint-focused architecture notes.
- `DEV_NOTES.md` – tradeoffs, rough edges, and current development notes.

---

## ✨ Features

- **Ticket search console**
  - Keyword-based search (`/api/search`) across ticket summaries and descriptions.
  - Optional **AI semantic search** (`/api/semantic-search`) using vector embeddings.
  - “Use AI semantic search” toggle with a visible badge and per-result AI score.

- **Ticket inspector & feedback loop**
  - Click a ticket to open a detailed inspector panel.
  - Capture structured resolution feedback:
    - Did this resolve your issue? (**Yes/No**)
    - What did you do to resolve it? (free-text notes)
    - Rating (1–5)
    - Original query text
  - Feedback is persisted to a `ticketfeedback` table via `/api/ticket-feedback/`.

- **Insights (patterns) view**
  - `/api/patterns/summary` aggregates all feedback:
    - Total feedback count
    - Tickets with unresolved feedback
    - Top unresolved tickets with counts
  - **Insights tab** in the UI shows:
    - A small metrics row (total feedback, unresolved tickets, most unresolved ticket)
    - A “Top Unresolved Tickets” list
  - Clicking a ticket in Insights jumps back to the Search tab and (when possible) highlights that ticket in the results.

- **Developer experience**
  - Canonical SQLite DB in the repo root (`echohelp.db`) with helper scripts:
    - `db_init.sh` – create tables (optionally seed demo data)
    - `db_reset.sh` – drop & recreate DB (optionally seed demo data)
  - Semantic embeddings backfill script: `scripts/backfill_ticket_embeddings.py`.
  - GitHub Actions CI pipeline running `ruff`, `pyright`, and `pytest`.
  - Production build via Vite (`npm run build` in `frontend/`).

---

## 🧱 Architecture

**Backend**

- **Framework:** FastAPI
- **ORM:** SQLModel
- **Database:** SQLite (`echohelp.db` in repo root)
- **Key modules:**
  - `backend/app/api/search.py` – keyword ticket search (`/api/search`)
  - `backend/app/api/semantic_search.py` – embedding-based semantic search (`/api/semantic-search`)
  - `backend/app/api/routes/ticket_feedback.py` – feedback endpoint (`/api/ticket-feedback/`)
  - `backend/app/api/routes/patterns.py` – feedback patterns summary (`/api/patterns/summary`)
  - `backend/app/services/embeddings.py` – embedding helper + model loading
  - `backend/app/models/ticket.py` – ticket model
  - `backend/app/models/ticket_feedback.py` – feedback model
  - `backend/app/models/embedding.py` – ticket embedding model
  - `backend/app/db_init.py` – DB init + seeding

**Frontend**

- **Framework:** React + TypeScript
- **Bundler/Dev:** Vite
- **Styling:** Tailwind CSS
- **Key components:**
  - `frontend/src/Search.tsx` – main search console + feedback UI + Insights tab
    - Keyword vs AI semantic search toggle
    - Results list + ticket inspector
    - Feedback form and submit handler
    - Insights tab with patterns summary and click-through to Search

**CI / Tooling**

- `ruff` for linting
- `pyright` for static type checking
- `pytest` for tests
- GitHub Actions workflow in `.github/workflows/ci.yml`

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+ (or compatible version used in the repo)
- Node.js + npm
- (Optional) `virtualenv` / `venv` for Python dependencies

### 1. Clone and install backend dependencies

```bash
git clone <your-repo-url>.git
cd Echo-Help   # or your repo folder

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

pip install -r backend/requirements.txt
```

### 2. Initialize the database

From the repo root:

```bash
chmod +x scripts/db_init.sh scripts/db_reset.sh

# Create tables
./scripts/db_init.sh

# Or, if you want a completely fresh DB:
./scripts/db_reset.sh

# Optional: seed demo org data (explicit opt-in)
SEED_DEMO=1 ./scripts/db_reset.sh
# (alias)
ECHOHELP_SEED_DEMO=1 ./scripts/db_reset.sh
```

If embeddings are not yet populated, run:

```bash
PYTHONPATH=. python3 scripts/backfill_ticket_embeddings.py
```

Troubleshooting:

- If you pull new code and see 500s that mention a missing SQLite column/table, your local `echohelp.db` is likely older than the current schema. The quickest fix is: `./scripts/db_reset.sh`.

### 3. Run the backend

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8001
```

The API root will be at: `http://127.0.0.1:8001`.

### 🚀 Quick Demo (Search)

A tiny CLI demo script is included to exercise the real HTTP API and print friendly results.

1. Start the backend (from the repo root):

```bash
# Example: start the FastAPI dev server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8001
```

2. Run the demo script (defaults to `http://localhost:8001`):

```bash
PYTHONPATH=. python -m scripts.demo_echohelp
```

If your backend is running on a different host/port, set `ECHOHELP_API_BASE`:

```bash
export ECHOHELP_API_BASE="http://127.0.0.1:8001"
PYTHONPATH=. python -m scripts.demo_echohelp
```

The script issues a few example queries and prints a compact list of matching tickets (id, title, snippet, source).

### 🔄 Ingest → Search Demo (End-to-End)

This demo mode ingests a synthetic conversation thread and then searches for it to show the full
pipeline: ingest -> embedding -> search.

1. Start the backend (from the repo root):

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8001
```

2. Run the ingest→search demo:

```bash
PYTHONPATH=. python -m scripts.demo_echohelp --mode ingest-search
```

This will POST a small synthetic thread to `/api/ingest/thread`, wait briefly for embedding,
and then call `/api/search` to look up the ingested content. The script prints the ingest
response followed by the search results.

If you see zero results, check that the backend you're running is the same one used by the demo
script (use `ECHOHELP_API_BASE` to point to another host/port).

### 🧪 Ask Echo baseline evaluation (offline)

If you’ve collected some Ask Echo feedback (via the UI or `POST /api/ask-echo/feedback`), you can export labeled rows from the DB and evaluate a simple threshold baseline:

```bash
bash scripts/dev_eval_ask_echo_baseline.sh --grid-search
```

Optional (more realistic): reserve the newest 20% as a test set, optimize thresholds on train, and show a per-`mode` breakdown:

```bash
bash scripts/dev_eval_ask_echo_baseline.sh --grid-search --test-ratio 0.2 --by-mode
```

This script writes a JSON export to `/tmp/ask_echo_training_export.json` and prints metrics + a small calibration table.



### 4. Install frontend dependencies and run dev server

```bash
cd frontend
npm install
npm run dev
```

By default Vite will start on `http://localhost:5174`.

Tip: from the repo root you can run backend + frontend together via:

```bash
npm run dev
```

### 5. Build frontend for production

From `frontend/`:

```bash
npm run build
```

---

## 🔍 Key API Endpoints

All endpoints are prefixed with `/api`.

### `POST /api/search`

Keyword search across tickets using SQL `ILIKE`.

**Request body:**

```json
{
  "q": "password reset"
}
```

**Response:**

```json
[
  {
    "id": 1,
    "summary": "Password reset not working",
    "description": "User cannot reset password via portal...",
    ...
  }
]
```

---

### `POST /api/ask-echo`

Ask Echo answers a question and returns explicit suggestions for tickets/snippets.

**Request body:**

```json
{
  "q": "vpn auth_failed",
  "limit": 5
}
```

**Response (v2):**

```json
{
  "meta": { "kind": "ask_echo", "version": "v2" },
  "query": "vpn auth_failed",
  "answer": "...",
  "answer_kind": "grounded",
  "ask_echo_log_id": 123,
  "suggested_tickets": [{ "id": 42, "summary": "VPN auth_failed when connecting" }],
  "suggested_snippets": [{ "id": 7, "title": "VPN auth fix", "echo_score": 0.9, "ticket_id": 42 }],
  "kb_backed": true,
  "kb_confidence": 0.9,
  "mode": "kb_answer",
  "references": [{ "ticket_id": 42, "confidence": 0.78 }],
  "reasoning": {
    "candidate_snippets": [{ "id": 7, "title": "VPN auth fix", "score": 0.9 }],
    "chosen_snippet_ids": [7],
    "echo_score": 0.9
  }
}
```

Note: older clients expecting `results`/`snippets` should be updated to use `suggested_tickets`/`suggested_snippets`.

---

### `POST /api/semantic-search`

Embedding-based semantic search using precomputed ticket embeddings.

**Request body:**

```json
{
  "q": "password reset issues",
  "limit": 5
}
```

**Response:**

```json
[
  {
    "id": 1,
    "summary": "Password reset not working",
    "description": "User cannot reset password via portal...",
    "ai_score": 0.91
  },
  ...
]
```

(The exact shape may differ slightly depending on how you normalize `ai_score` on the frontend.)

---

### `POST /api/ticket-feedback/`

Record feedback on a ticket.

**Request body:**

```json
{
  "ticket_id": 1,
  "rating": 4,
  "helped": true,
  "resolution_notes": "Cleared browser cache and retried",
  "query_text": "password reset not working"
}
```

---

### `GET /api/patterns/summary`

Return aggregated feedback statistics.

**Sample response:**

```json
{
  "total_feedback": 12,
  "by_ticket": [
    {
      "ticket_id": 1,
      "summary": "Password reset not working",
      "total_feedback": 5,
      "unresolved": 2
    }
  ],
  "top_unresolved": [
    {
      "ticket_id": 1,
      "summary": "Password reset not working",
      "total_feedback": 5,
      "unresolved": 2
    }
  ]
}
```

---

## 🧪 Testing & CI

Run backend tests from the repo root:

```bash
PYTHONPATH=$PWD pytest
```

Run a focused feedback endpoint test:

```bash
PYTHONPATH=$PWD pytest tests/test_ticket_feedback_endpoint.py
```

CI (GitHub Actions) will automatically:

* Install backend dependencies
* Run `ruff`, `pyright`, and `pytest` on push / pull request

---

## 🗺️ Roadmap / Ideas

* More advanced pattern analysis (clusters, time-series of unresolved issues).
* Attachments and richer ticket metadata.
* Integrations with existing ticketing tools (Jira, Zendesk, etc.).
* Authentication / multi-tenant support.
* Deeper AI features: suggested KB articles, automated troubleshooting flows.

---

## 🎯 Why this project

EchoHelp is designed as a realistic full-stack portfolio project:

* Shows experience with **Python/FastAPI/SQLModel** and **React/TypeScript/Tailwind**.
* Demonstrates **AI integration** via semantic search and embeddings.
* Includes **CI, tests, and DB tooling**, not just a demo UI.
* Models a real-world use case for IT teams: turning support tickets into a growing knowledge base and analytics engine.

---

## 🎬 Demo (Will Be Added After MVP)

Video walkthrough will be added once core features are functional and integrated.

---

## 📩 Contact / Notes

Internal project for experimental and professional development.
Not yet affiliated with any employer or organization.
