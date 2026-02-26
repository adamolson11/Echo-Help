from __future__ import annotations

import re
from dataclasses import dataclass

from sqlmodel import Session, select

from backend.app.models.kb_entry import KBEntry


@dataclass(frozen=True)
class KBSearchResult:
    entry: KBEntry
    score: float


def _tokens(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-z0-9_]+", (text or "").lower()) if len(tok) >= 2}


def _is_howto_query(query: str) -> bool:
    q = (query or "").lower()
    return any(key in q for key in ("how do i", "how to", "steps", "setup", "configure"))


def search_kb_entries(*, session: Session, query: str, limit: int = 3) -> list[KBSearchResult]:
    rows = list(session.exec(select(KBEntry)).all())
    q_tokens = _tokens(query)
    howto = _is_howto_query(query)

    scored: list[KBSearchResult] = []
    for row in rows:
        hay = _tokens(f"{row.title}\n{row.body_markdown}\n{' '.join(row.tags or [])}")
        overlap = float(len(q_tokens & hay)) / float(max(len(q_tokens), 1))
        howto_boost = 0.15 if howto else 0.0
        score = overlap + howto_boost
        if score <= 0.0:
            continue
        scored.append(KBSearchResult(entry=row, score=score))

    scored.sort(key=lambda item: (item.score, item.entry.updated_at.timestamp(), item.entry.entry_id), reverse=True)
    return scored[: max(1, limit)]
