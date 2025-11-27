# Echo-Help
A support tool fot CMS ticketing systems
EchoHelp
AI-Powered Support Intelligence & Living Knowledge System

MVP Scope • Private Repository (v0.1)

📌 Overview

EchoHelp is an AI-driven support intelligence platform that sits on top of existing ticketing and knowledge systems (e.g., Jira, Confluence).
It transforms how support teams search, categorize, resolve, and continually improve their documentation.

At its core, EchoHelp turns a single natural-language problem description into:

Predicted ticket fields (category, subcategory, tags)

Relevant historical tickets and docs (semantic ranking)

Suggested standardized phrasing (canonical terms)

A feedback-driven improvement loop for solution accuracy

A living, self-auditing knowledge base enriched by real agent input

The system evolves with every interaction, slowly building a semantic understanding of an organization’s support landscape.

🎯 MVP Goals

The initial MVP focuses on a tightly scoped, high-impact vertical slice:

1. Natural Language Intake → Structured Ticket Prediction

Convert a customer sentence into predicted category/subcategory/tags.

Suggest canonical language via embeddings-based similarity.

Auto-fill a ticket form (editable by agents).

2. Semantic Search Over Tickets & Docs

Jira ingestion for a test project.

Embedding-based similarity for:

historical tickets

KB documents

Rank results based on:

semantic relevance

usefulness feedback

3. Agent Feedback → Continuous Learning

“Did this help?” rating system.

Use feedback to adjust future ranking.

Foundation for a self-improving search engine.

4. Document Viewer with Concept Highlighting (v0.1)

Basic in-app article viewer.

Highlight phrases → create early-stage concept markers.

Store concept mentions for future graph linking.

5. Clean Architecture • Modest UI • Demo Ready

FastAPI backend

Next.js frontend

Embedding model: sentence-transformers

Local Postgres or SQLite

Can be deployed to Vercel/Render for demonstration

The MVP aims to prove the intelligence layer works and show the future potential of a fully self-evolving support knowledge system.

🧱 Architecture Summary (Simplified MVP)
Backend (FastAPI)

/intake: analyze text → structured fields + suggestions

/search: semantic + keyword hybrid ranking

/feedback: store helpfulness ratings

Jira ingestion tasks (tickets + comments)

Embedding generator service

Vector search + ranking logic

Frontend (Next.js)

Intake page (text → predicted fields → suggestions)

Search results page

Simple article viewer (with concept highlighting)

Basic analytics placeholder

Database

tickets

documents

embeddings

categories

canonical_terms

feedback

concepts + concept_mentions (stubbed for future)

📁 Repository Structure (Recommended)
echohelp/
  README.md
  docs/
    PRODUCT_BRIEF.md
    ARCHITECTURE_V0.md
    WIREFRAMES.md
    ROADMAP.md
    DATA_MODEL.md
  backend/
    app/
      main.py
      api/
      models/
      services/
      vector/
    tests/
  frontend/
    src/
      app/
      components/
      lib/
  scripts/
    ingest_jira.py
    ingest_docs.py
  examples/
    sample_tickets/
    sample_kb/

🚀 MVP Feature Checklist
🔌 Jira Integration

 Connect to test Jira Cloud project

 Pull issues + comments

 Normalize to DB

 Trigger manual sync

🧠 Semantic Engine

 Encode tickets/docs with embeddings

 Vector search engine

 Hybrid scoring (keyword + semantic)

📝 AI Intake Assistant

 Predict category/subcategory/tags

 Suggest canonical terms

 Show related tickets

 Show related docs

 Prefill ticket form

⭐ Suggestions Engine

 Rank tickets/docs

 Short summaries (LLM optional)

 “Did this help?” feedback capture

🔄 Feedback Loop

 Store ratings

 Adjust ranking weights

 Basic trend stats

📚 Early Knowledge Graph

 Highlight phrases in docs

 Store concept markers

 Link concepts to tickets/docs (v0.2)

🎛️ UI/UX

 Intake UI

 Search UI

 Article viewer

 Minimal analytics page

🌱 Future Expansion (Beyond MVP)
Knowledge Graph Layer

Concept nodes

Graph visualization

Tightly linked articles, tickets, clusters

Doc Enrichment Engine

Post-resolution agent input:

“What solved the issue that wasn’t in the doc?”

AI proposes fallback solutions

Peer-review workflow

Hygiene Engine

Content health scoring

Least-used article purge list

Rewrite/merge tools

Desktop Companion Agent

Local daemon

System info collector

Guided troubleshooting

AI-driven playbooks

Enterprise Connectors

Zendesk

ServiceNow

Salesforce Service Cloud

Confluence

GitHub Issues

🔒 Licensing

This project is currently private and proprietary.
Default license: All Rights Reserved until further structure or commercial licensing is defined.

🙌 Contributing (Private Stage)

Closed to external contributors.
Collaboration allowed by explicit invitation only.

🎬 Demo (Will Be Added After MVP)

Video walkthrough will be added once core features are functional and integrated.

📩 Contact / Notes

Internal project for experimental and professional development.
Not yet affiliated with any employer or organization.

### GET `/api/feedback-suggestions`

Returns the most common "actual fix" phrases from ticket feedback. This is
intended to power future insights features (e.g. surfacing missing knowledge
base articles based on what actually solved tickets in the field).

**Query parameters**

- `limit` (int, optional, default `50`): maximum number of phrases to return.

**Response**

```json
[
  {
    "phrase": "reset user password",
    "count": 14
  },
  {
    "phrase": "rebooted modem",
    "count": 8
  }
]
```
