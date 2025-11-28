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
    - `db_init.sh` – create tables and seed demo tickets
    - `db_reset.sh` – drop & recreate DB + seed data + backfill embeddings
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

# Create tables + seed demo tickets + (optionally) seed embeddings via db_init
./scripts/db_init.sh

# Or, if you want a completely fresh DB:
./scripts/db_reset.sh
```

If embeddings are not yet populated, run:

```bash
PYTHONPATH=. python3 scripts/backfill_ticket_embeddings.py
```

### 3. Run the backend

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The API root will be at: `http://127.0.0.1:8000`.

### 4. Install frontend dependencies and run dev server

```bash
cd frontend
npm install
npm run dev
```

By default Vite will start on something like `http://localhost:5173` or `http://localhost:5175` (check the terminal output).

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
