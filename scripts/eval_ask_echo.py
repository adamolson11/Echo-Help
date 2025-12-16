#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlmodel import Session

import backend.app.db as db
from backend.app.services.ask_echo_engine import AskEchoEngine, AskEchoEngineRequest


def main() -> None:
    p = argparse.ArgumentParser(description="Quick offline Ask Echo eval runner")
    p.add_argument("--queries", type=str, required=True, help="Path to a JSON list of query strings")
    p.add_argument("--limit", type=int, default=5)
    args = p.parse_args()

    queries_path = Path(args.queries)
    queries = json.loads(queries_path.read_text())
    if not isinstance(queries, list):
        raise SystemExit("--queries must be a JSON list")

    db.ensure_engine()
    if db.engine is None:
        raise SystemExit("Database engine is not initialized")
    eng = AskEchoEngine()

    out = []
    with Session(db.engine) as session:
        for q in queries:
            if not isinstance(q, str):
                continue
            r = eng.run(session=session, req=AskEchoEngineRequest(query=q, limit=args.limit))
            out.append(
                {
                    "query": q,
                    "answer_kind": r.answer_kind,
                    "kb_backed": r.kb_backed,
                    "kb_confidence": r.kb_confidence,
                    "mode": r.mode,
                    "references": [x.model_dump() for x in r.references],
                    "ticket_summaries": [x.model_dump() for x in r.ticket_summaries],
                }
            )

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
