from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from ..models.snippets import SnippetFeedback, SolutionSnippet
from ..models.ticket import Ticket


def extract_ticket_patterns(session: Session, days: int = 14) -> dict[str, Any]:
    """Compute simple ticket patterns over the last ``days`` days.

    Returns a JSON-serializable dict with:
    - top_keywords: list[{keyword, count}]
    - frequent_titles: list[{title, count}]
    - semantic_clusters: list[dict] (placeholder for now)
    - stats: {total_tickets, window_days}
    """

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(Ticket).where(Ticket.created_at >= cutoff)  # type: ignore[attr-defined]
    tickets: list[Ticket] = list(session.exec(stmt).all())

    total = len(tickets)

    word_counter: Counter[str] = Counter()
    title_counter: Counter[str] = Counter()

    first_created_at: datetime | None = None
    last_created_at: datetime | None = None

    for t in tickets:
        created = getattr(t, "created_at", None)
        if isinstance(created, datetime):
            if first_created_at is None or created < first_created_at:
                first_created_at = created
            if last_created_at is None or created > last_created_at:
                last_created_at = created
        title = (getattr(t, "title", None) or getattr(t, "summary", "") or "").strip()
        if title:
            title_counter[title] += 1

        parts: list[str] = []
        for attr in ("title", "summary", "description", "body"):
            value = getattr(t, attr, None)
            if isinstance(value, str):
                parts.append(value)
        text = " ".join(parts).lower()

        for word in _tokenize_words(text):
            word_counter[word] += 1

    top_keywords = [{"keyword": w, "count": c} for w, c in word_counter.most_common(25)]
    frequent_titles = [{"title": title, "count": c} for title, c in title_counter.most_common(25)]

    semantic_clusters: list[dict[str, Any]] = []

    return {
        "top_keywords": top_keywords,
        "frequent_titles": frequent_titles,
        "semantic_clusters": semantic_clusters,
        "stats": {
            "total_tickets": total,
            "window_days": days,
            "first_ticket_at": first_created_at.isoformat() if first_created_at else None,
            "last_ticket_at": last_created_at.isoformat() if last_created_at else None,
        },
        "meta": {
            "kind": "ticket",
            "version": "v1",
        },
    }


def _tokenize_words(text: str) -> list[str]:
    import re

    # Basic tokenization with a small, pragmatic stopword list so
    # Ticket Pattern Radar surfaces meaningful patterns instead of noise.
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "have",
        "has",
        "are",
        "was",
        "were",
        "issue",
        "ticket",
        "error",
        "problem",
        "help",
    }

    words: list[str] = []
    for word in re.findall(r"[a-z0-9_]+", text):
        if len(word) <= 2:
            continue
        if word in stopwords:
            continue
        words.append(word)
    return words


def get_snippet_pattern_radar(session: Session) -> dict[str, Any]:
    """Compute snippet-based pattern radar stats used by existing tests.

    Returns a JSON-serializable dict with:
    - stats: {total_snippets, total_successes, total_failures}
    - top_frequent_snippets: list[dict]
    - top_risky_snippets: list[dict]
    """

    total_snippets = session.exec(select(func.count(col(SolutionSnippet.id)))).one()

    feedback_rows: list[SnippetFeedback] = list(session.exec(select(SnippetFeedback)).all())
    counts: dict[int, dict[str, int]] = {}

    for fb in feedback_rows:
        sid = fb.snippet_id
        bucket = counts.setdefault(sid, {"total": 0, "successes": 0, "failures": 0})
        bucket["total"] += 1
        if fb.helped is True:
            bucket["successes"] += 1
        elif fb.helped is False:
            bucket["failures"] += 1

    total_successes = 0
    total_failures = 0

    frequent = []
    risky = []

    snippet_by_id: dict[int, SolutionSnippet] = {
        int(s.id): s for s in session.exec(select(SolutionSnippet)).all() if s.id is not None
    }

    for snippet_id, agg in counts.items():
        total = agg["total"]
        successes = agg["successes"]
        failures = agg["failures"]

        total_successes += successes
        total_failures += failures

        snippet = snippet_by_id.get(snippet_id)
        if not snippet:
            continue

        summary = snippet.summary or snippet.title or str(snippet.id)
        item = {
            "snippet_id": snippet.id,
            "problem_summary": summary,
            "total_uses": int(total),
            "successes": int(successes),
            "failures": int(failures),
        }

        frequent.append(item)

        if failures > 0:
            risky.append(item)

    frequent.sort(key=lambda x: x["total_uses"], reverse=True)
    risky.sort(key=lambda x: x["failures"], reverse=True)

    return {
        "stats": {
            "total_snippets": int(total_snippets or 0),
            "total_successes": int(total_successes),
            "total_failures": int(total_failures),
        },
        "top_frequent_snippets": frequent[:10],
        "top_risky_snippets": risky[:10],
        "meta": {
            "kind": "snippet",
            "version": "v1",
        },
    }
