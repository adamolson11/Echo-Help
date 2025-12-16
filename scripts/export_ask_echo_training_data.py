#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta

from sqlmodel import Session, select

import backend.app.db as db
from backend.app.models.ask_echo_feedback import AskEchoFeedback
from backend.app.models.ask_echo_log import AskEchoLog


def _safe_json_loads(s: str | None) -> dict:
    if not s:
        return {}
    try:
        v = json.loads(s)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def main() -> None:
    p = argparse.ArgumentParser(description="Export Ask Echo feedback rows joined to features for ML training")
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--limit", type=int, default=5000)
    args = p.parse_args()

    if args.days <= 0:
        raise SystemExit("--days must be positive")

    db.ensure_engine()
    if db.engine is None:
        raise SystemExit("Database engine is not initialized")
    cutoff = datetime.utcnow() - timedelta(days=args.days)

    out: list[dict] = []
    with Session(db.engine) as session:
        stmt = (
            select(AskEchoFeedback)
            .where(AskEchoFeedback.created_at >= cutoff)  # type: ignore[attr-defined]
            .order_by(AskEchoFeedback.created_at.desc())  # type: ignore[attr-defined]
            .limit(args.limit)
        )
        feedback_rows = list(session.exec(stmt).all())

        for fb in feedback_rows:
            log = session.get(AskEchoLog, fb.ask_echo_log_id)
            if not log:
                continue

            notes_obj = _safe_json_loads(log.reasoning_notes)
            features = notes_obj.get("features") if isinstance(notes_obj.get("features"), dict) else {}

            out.append(
                {
                    "ask_echo_log_id": fb.ask_echo_log_id,
                    "created_at": fb.created_at.isoformat() if fb.created_at else None,
                    "label_helped": bool(fb.helped),
                    "notes": fb.notes,
                    "query": log.query,
                    "mode": log.mode,
                    "top_ticket_score": log.top_score,
                    "kb_confidence": log.kb_confidence,
                    "echo_score": log.echo_score,
                    "references_count": log.references_count,
                    "features": features,
                }
            )

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
