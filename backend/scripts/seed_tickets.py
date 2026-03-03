from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from backend.app.db import SessionLocal, init_db
from backend.app.models.embedding import Embedding
from backend.app.models.snippets import SnippetFeedback, SolutionSnippet
from backend.app.models.ticket import Ticket
from backend.app.models.ticket_feedback import TicketFeedback

DEFAULT_SOURCE = "seed_jira_v1"
DEFAULT_PATH = Path("backend/app/seed_data/tickets_big_seed.jsonl")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _ticket_body(row: dict) -> str:
    steps = row.get("resolution_good") or []
    steps_md = "\n".join(f"- {str(step)}" for step in steps if str(step).strip())
    repro = row.get("repro_steps") or []
    repro_md = "\n".join(f"- {str(step)}" for step in repro if str(step).strip())
    return (
        f"# {row.get('title', '')}\n\n"
        f"## Description\n{row.get('description', '')}\n\n"
        f"## Expected\n{row.get('expected', '')}\n\n"
        f"## Actual\n{row.get('actual', '')}\n\n"
        f"## Repro Steps\n{repro_md}\n\n"
        f"## Good Resolution\n{steps_md}\n"
    )


def _normalize_tags(row: dict) -> list[str]:
    raw_tags = row.get("tags")
    tags = raw_tags if isinstance(raw_tags, list) else []
    out = [str(tag).strip().lower() for tag in tags if str(tag).strip()]
    if row.get("product_area"):
        out.append(f"area:{str(row['product_area']).strip().lower()}")
    if row.get("severity"):
        out.append(f"severity:{str(row['severity']).strip().lower()}")
    if row.get("priority"):
        out.append(f"priority:{str(row['priority']).strip().lower()}")
    if row.get("environment"):
        out.append(f"env:{str(row['environment']).strip().lower()}")
    out.append(f"fix_confirmed:{str(bool(row.get('fix_confirmed_good', False))).lower()}")
    if row.get("answer_quality_label"):
        out.append(f"answer_quality:{str(row.get('answer_quality_label')).strip().lower()}")
    return sorted(set(out))


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            yield json.loads(text)


def summarize_rows(rows: list[dict]) -> dict[str, dict[str, int]]:
    return {
        "product_area": dict(sorted(Counter(str(r.get("product_area") or "unknown") for r in rows).items())),
        "environment": dict(sorted(Counter(str(r.get("environment") or "unknown") for r in rows).items())),
        "severity": dict(sorted(Counter(str(r.get("severity") or "unknown") for r in rows).items())),
    }


def _delete_seeded_rows(session: Session, *, source: str) -> None:
    seeded = list(session.exec(select(Ticket).where(Ticket.source == source)).all())
    seeded_ids = [int(t.id) for t in seeded if t.id is not None]
    if not seeded_ids:
        return

    snippets = list(session.exec(select(SolutionSnippet).where(SolutionSnippet.ticket_id.in_(seeded_ids))).all())  # type: ignore[reportAttributeAccessIssue]
    snippet_ids = [int(s.id) for s in snippets if s.id is not None]

    if snippet_ids:
        for fb in list(session.exec(select(SnippetFeedback).where(SnippetFeedback.snippet_id.in_(snippet_ids))).all()):  # type: ignore[reportAttributeAccessIssue]
            session.delete(fb)

    for row in list(session.exec(select(TicketFeedback).where(TicketFeedback.ticket_id.in_(seeded_ids))).all()):  # type: ignore[reportAttributeAccessIssue]
        session.delete(row)

    for row in list(session.exec(select(Embedding).where(Embedding.ticket_id.in_(seeded_ids))).all()):  # type: ignore[reportAttributeAccessIssue]
        session.delete(row)

    for row in snippets:
        session.delete(row)

    for row in seeded:
        session.delete(row)

    session.commit()


def seed_tickets(*, path: Path, reset: bool = False, source: str = DEFAULT_SOURCE, dry_run: bool = False) -> int:
    init_db()
    if not path.exists():
        raise FileNotFoundError(path)
    payload = list(_iter_jsonl(path))

    if dry_run:
        hist = summarize_rows(payload)
        print(f"dry_run rows={len(payload)}")
        print("histogram.product_area", hist["product_area"])
        print("histogram.environment", hist["environment"])
        print("histogram.severity", hist["severity"])
        return len(payload)

    with SessionLocal() as session:
        if reset:
            _delete_seeded_rows(session, source=source)

        inserted_or_updated = 0
        for row in payload:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key") or "").strip()
            title = str(row.get("title") or "").strip()
            if not key or not title:
                continue

            existing = session.exec(select(Ticket).where(Ticket.external_key == key)).first()
            created_at = _parse_dt(row.get("created_at")) or datetime.utcnow()
            resolved_at = _parse_dt(row.get("resolved_at"))
            fix_confirmed = bool(row.get("fix_confirmed_good", False))
            status = str(row.get("status") or ("closed" if fix_confirmed else "open"))
            project_key = key.split("-", 1)[0] if "-" in key else "ECHO"

            if existing is None:
                existing = Ticket(
                    key=key,
                    short_id=key,
                    external_key=key,
                    source=source,
                    source_system=str(row.get("source_system") or "seed"),
                    source_id=str(row.get("source_id") or "") or None,
                    source_url=str(row.get("source_url") or "") or None,
                    project_key=project_key,
                    summary=title,
                    description=str(row.get("description") or ""),
                    body_md=_ticket_body(row),
                    root_cause=str(row.get("root_cause_good") or "") or None,
                    root_cause_good=str(row.get("root_cause_good") or "") or None,
                    root_cause_bad=str(row.get("root_cause_bad") or "") or None,
                    bad_reason=str(row.get("bad_reason") or "") or None,
                    environment=str(row.get("environment") or "") or None,
                    owning_team=str(row.get("owning_team") or "") or None,
                    escalation_target=str(row.get("escalation_target") or "") or None,
                    product_area=str(row.get("product_area") or "") or None,
                    severity=str(row.get("severity") or "") or None,
                    tags=_normalize_tags(row),
                    repro_steps=[str(x) for x in (row.get("repro_steps") or []) if str(x).strip()] or None,
                    expected_result=str(row.get("expected") or "") or None,
                    actual_result=str(row.get("actual") or "") or None,
                    resolution_good=[str(x) for x in (row.get("resolution_good") or []) if str(x).strip()] or None,
                    fix_confirmed_good=fix_confirmed,
                    resolution_bad=[str(x) for x in (row.get("resolution_bad") or []) if str(x).strip()] or None,
                    answer_quality_label=str(row.get("answer_quality_label") or "") or None,
                    status=status,
                    priority=str(row.get("priority") or "") or None,
                    created_at=created_at,
                    updated_at=created_at,
                    resolved_at=resolved_at,
                )
                session.add(existing)
            else:
                existing.key = key
                existing.short_id = key
                existing.source = source
                existing.source_system = str(row.get("source_system") or "seed")
                existing.source_id = str(row.get("source_id") or "") or None
                existing.source_url = str(row.get("source_url") or "") or None
                existing.project_key = project_key
                existing.summary = title
                existing.description = str(row.get("description") or "")
                existing.body_md = _ticket_body(row)
                existing.root_cause = str(row.get("root_cause_good") or "") or None
                existing.root_cause_good = str(row.get("root_cause_good") or "") or None
                existing.root_cause_bad = str(row.get("root_cause_bad") or "") or None
                existing.bad_reason = str(row.get("bad_reason") or "") or None
                existing.environment = str(row.get("environment") or "") or None
                existing.owning_team = str(row.get("owning_team") or "") or None
                existing.escalation_target = str(row.get("escalation_target") or "") or None
                existing.product_area = str(row.get("product_area") or "") or None
                existing.severity = str(row.get("severity") or "") or None
                existing.tags = _normalize_tags(row)
                existing.repro_steps = [str(x) for x in (row.get("repro_steps") or []) if str(x).strip()] or None
                existing.expected_result = str(row.get("expected") or "") or None
                existing.actual_result = str(row.get("actual") or "") or None
                existing.resolution_good = [str(x) for x in (row.get("resolution_good") or []) if str(x).strip()] or None
                existing.fix_confirmed_good = fix_confirmed
                existing.resolution_bad = [str(x) for x in (row.get("resolution_bad") or []) if str(x).strip()] or None
                existing.answer_quality_label = str(row.get("answer_quality_label") or "") or None
                existing.status = status
                existing.priority = str(row.get("priority") or "") or None
                existing.created_at = created_at
                existing.updated_at = created_at
                existing.resolved_at = resolved_at
                session.add(existing)

            inserted_or_updated += 1

        session.commit()
        return inserted_or_updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed realistic Jira-like tickets for Ask Echo demos")
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH, help="Path to JSONL seed file")
    parser.add_argument("--source", type=str, default=DEFAULT_SOURCE, help="Ticket source marker for idempotent reset")
    parser.add_argument("--reset", action="store_true", help="Delete existing rows for this source before seed")
    parser.add_argument("--dry-run", action="store_true", help="Parse file and print histogram summary without DB writes")
    args = parser.parse_args()

    started = time.perf_counter()
    count = seed_tickets(path=args.path, reset=args.reset, source=args.source, dry_run=args.dry_run)
    elapsed = time.perf_counter() - started
    mode = "dry-run" if args.dry_run else "seed"
    print(f"{mode} completed rows={count} path={args.path} elapsed_s={elapsed:.3f}")


if __name__ == "__main__":
    main()
