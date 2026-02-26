from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlmodel import select

from backend.app.db import SessionLocal, init_db
from backend.app.models.kb_entry import KBEntry

DEFAULT_PATH = Path("backend/app/seed_data/kb_seed.jsonl")
DEFAULT_SOURCE = "seed_kb"


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _summary(rows: list[dict]) -> dict[str, dict[str, int]]:
    return {
        "product_area": dict(sorted(Counter(str(r.get("product_area") or "unknown") for r in rows).items())),
        "source_system": dict(sorted(Counter(str(r.get("source_system") or DEFAULT_SOURCE) for r in rows).items())),
    }


def seed_kb(*, path: Path, reset: bool = False, dry_run: bool = False, source_system: str = DEFAULT_SOURCE) -> int:
    init_db()
    rows = list(_iter_jsonl(path))

    if dry_run:
        hist = _summary(rows)
        print(f"dry_run rows={len(rows)}")
        print("histogram.product_area", hist["product_area"])
        print("histogram.source_system", hist["source_system"])
        return len(rows)

    with SessionLocal() as session:
        if reset:
            existing = list(session.exec(select(KBEntry).where(KBEntry.source_system == source_system)).all())
            for row in existing:
                session.delete(row)
            session.commit()

        count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            entry_id = str(row.get("id") or "").strip()
            title = str(row.get("title") or "").strip()
            body = str(row.get("body_markdown") or "").strip()
            if not entry_id or not title or not body:
                continue

            existing = session.exec(select(KBEntry).where(KBEntry.entry_id == entry_id)).first()
            if existing is None:
                existing = KBEntry(
                    entry_id=entry_id,
                    title=title,
                    body_markdown=body,
                    tags=[str(t).strip().lower() for t in (row.get("tags") or []) if str(t).strip()] or None,
                    product_area=str(row.get("product_area") or "") or None,
                    updated_at=_parse_dt(str(row.get("updated_at") or "")),
                    source_system=str(row.get("source_system") or source_system),
                    source_url=str(row.get("source_url") or "") or None,
                )
                session.add(existing)
            else:
                existing.title = title
                existing.body_markdown = body
                existing.tags = [str(t).strip().lower() for t in (row.get("tags") or []) if str(t).strip()] or None
                existing.product_area = str(row.get("product_area") or "") or None
                existing.updated_at = _parse_dt(str(row.get("updated_at") or ""))
                existing.source_system = str(row.get("source_system") or source_system)
                existing.source_url = str(row.get("source_url") or "") or None
                session.add(existing)
            count += 1

        session.commit()
        return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed KB entries from JSONL")
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--source-system", type=str, default=DEFAULT_SOURCE)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    count = seed_kb(path=args.path, reset=args.reset, dry_run=args.dry_run, source_system=args.source_system)
    elapsed = time.perf_counter() - started
    mode = "dry-run" if args.dry_run else "seed"
    print(f"{mode} completed rows={count} path={args.path} elapsed_s={elapsed:.3f}")


if __name__ == "__main__":
    main()
