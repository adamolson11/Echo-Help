from __future__ import annotations

from typing import List

from sqlmodel import Session, select

from ..models.snippets import SolutionSnippet
from ..schemas.insights import (PatternRadarResponse, PatternRadarStats,
                                SnippetPatternSummary)

TOP_N = 5


def get_pattern_radar_summary(session: Session) -> PatternRadarResponse:
    query = select(SolutionSnippet)
    snippets: List[SolutionSnippet] = list(session.exec(query).all())

    total_snippets = len(snippets)
    total_successes = sum((s.success_count or 0) for s in snippets)
    total_failures = sum((s.failure_count or 0) for s in snippets)

    # Frequent: highest total attempts
    frequent_sorted = sorted(
        snippets,
        key=lambda s: ((s.success_count or 0) + (s.failure_count or 0)),
        reverse=True,
    )

    # Risky: sort by failure rate first, then by low echo_score
    def failure_rate(s: SolutionSnippet) -> float:
        total = (s.success_count or 0) + (s.failure_count or 0)
        if total <= 0:
            return 0.0
        return (s.failure_count or 0) / total

    risky_sorted = sorted(
        snippets,
        key=lambda s: (failure_rate(s), 1.0 - (s.echo_score or 0.0)),
        reverse=True,
    )

    def to_summary(s: SolutionSnippet) -> SnippetPatternSummary:
        total = (s.success_count or 0) + (s.failure_count or 0)
        fr = (s.failure_count or 0) / total if total > 0 else 0.0
        return SnippetPatternSummary(
            id=s.id or 0,
            problem_summary=(s.summary or s.title or "")[:1000],
            echo_score=(s.echo_score or 0.0),
            success_count=(s.success_count or 0),
            failure_count=(s.failure_count or 0),
            failure_rate=round(fr, 4),
            source_ticket_id=(s.ticket_id if hasattr(s, "ticket_id") else None),
        )

    top_frequent = [to_summary(s) for s in frequent_sorted[:TOP_N]]
    top_risky = [to_summary(s) for s in risky_sorted[:TOP_N]]

    stats = PatternRadarStats(
        total_snippets=total_snippets,
        total_successes=total_successes,
        total_failures=total_failures,
    )

    return PatternRadarResponse(
        stats=stats,
        top_frequent_snippets=top_frequent,
        top_risky_snippets=top_risky,
    )
