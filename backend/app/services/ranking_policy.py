from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func
from sqlmodel import Session, select

from ..models.snippets import SolutionSnippet
from ..models.ticket import Ticket
from ..models.ticket_feedback import TicketFeedback


@dataclass(frozen=True)
class RankedTicket:
    score: float
    ticket: Ticket


@dataclass(frozen=True)
class RankedSnippet:
    score: float
    snippet: SolutionSnippet


def _safe_dt(value: datetime | None) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _keyword_match_score(*, query: str, haystack: str) -> float:
    q = (query or "").strip().lower()
    if not q:
        return 0.0
    return 1.0 if q in (haystack or "").lower() else 0.0


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi <= lo:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _ticket_feedback_maps(session: Session, *, ticket_ids: list[int]) -> tuple[dict[int, float], dict[int, float]]:
    """Return (feedback_ratio_score, usage_score) in [0,1] for each ticket_id."""
    if not ticket_ids:
        return {}, {}

    helped_true = func.sum(case((TicketFeedback.helped.is_(True), 1), else_=0))  # type: ignore[reportAttributeAccessIssue]
    helped_false = func.sum(case((TicketFeedback.helped.is_(False), 1), else_=0))  # type: ignore[reportAttributeAccessIssue]
    total = func.count()

    rows = list(
        session.exec(
            select(
                TicketFeedback.ticket_id,
                helped_true,
                helped_false,
                total,
            )
            .where(TicketFeedback.ticket_id.in_(ticket_ids))  # type: ignore[reportAttributeAccessIssue]
            .group_by(TicketFeedback.ticket_id)  # type: ignore[reportArgumentType]
        ).all()
    )

    ratio_map: dict[int, float] = {}
    usage_raw: dict[int, float] = {}
    for ticket_id, t_true, t_false, t_total in rows:
        tt = int(t_true or 0)
        tf = int(t_false or 0)
        tot = int(t_total or 0)

        # Map (-1..1) -> (0..1); neutral when no explicit helped true/false.
        if tot > 0:
            raw = (float(tt) - float(tf)) / float(tot)
            ratio_map[int(ticket_id)] = (raw + 1.0) / 2.0
            usage_raw[int(ticket_id)] = float(tot)

    # Normalize usage counts to 0..1
    # Important for determinism: DB group-by row order isn't guaranteed.
    ids = sorted(usage_raw.keys())
    if not ids:
        return ratio_map, {}

    usage_vals = [usage_raw[i] for i in ids]
    usage_norm = _normalize(usage_vals)
    usage_map = {i: usage_norm[idx] for idx, i in enumerate(ids)}

    return ratio_map, usage_map


def rank_tickets(
    session: Session,
    *,
    candidates: list[Ticket],
    query: str,
    semantic_scores: dict[int, float] | None = None,
) -> list[RankedTicket]:
    """Rank ticket candidates deterministically.

    Signals (v1): semantic similarity, keyword match, recency, feedback ratio, usage count.
    """
    semantic_scores = semantic_scores or {}

    ticket_ids: list[int] = [int(t.id) for t in candidates if t.id is not None]
    feedback_ratio_map, usage_map = _ticket_feedback_maps(session, ticket_ids=ticket_ids)

    # Compute recency in a way that does NOT depend on candidate list order.
    created_by_tid: dict[int, datetime] = {
        int(t.id): (_safe_dt(getattr(t, "created_at", None)) or datetime.min)
        for t in candidates
        if t.id is not None
    }

    tids_sorted = sorted(created_by_tid.keys())
    recency_norm_by_tid: dict[int, float] = {}
    if tids_sorted:
        created_ts_sorted = [created_by_tid[tid].timestamp() for tid in tids_sorted]
        norm_sorted = _normalize(created_ts_sorted)
        recency_norm_by_tid = {tid: norm_sorted[i] for i, tid in enumerate(tids_sorted)}

    ranked: list[RankedTicket] = []
    for t in candidates:
        tid = int(t.id) if t.id is not None else -1
        semantic = float(semantic_scores.get(tid, 0.0) or 0.0)

        haystack = f"{getattr(t, 'summary', '')}\n{getattr(t, 'description', '')}\n{getattr(t, 'external_key', '')}"
        keyword = _keyword_match_score(query=query, haystack=haystack)

        feedback = float(feedback_ratio_map.get(tid, 0.5))
        usage = float(usage_map.get(tid, 0.0))
        recency = float(recency_norm_by_tid.get(tid, 0.0)) if tid != -1 else 0.0

        # Weights are intentionally simple and explicit (no hidden heuristics).
        score = (
            0.55 * semantic
            + 0.25 * keyword
            + 0.10 * feedback
            + 0.05 * usage
            + 0.05 * recency
        )

        ranked.append(RankedTicket(float(score), t))  # type: ignore[reportCallIssue]

    def _sort_key(r: RankedTicket):
        t = r.ticket
        created_at = _safe_dt(getattr(t, "created_at", None)) or datetime.min
        tid = int(getattr(t, "id", -1) or -1)
        return (r.score, created_at.timestamp(), tid)

    ranked.sort(key=_sort_key, reverse=True)
    return ranked


def rank_snippets(*, candidates: list[SolutionSnippet], query: str) -> list[RankedSnippet]:
    """Rank snippet candidates deterministically.

    Signals (v1): keyword match, recency, feedback score, usage count.
    Note: snippet.echo_score is treated as the primary feedback-derived score.
    """
    # Normalize recency/usage in a way that does NOT depend on candidate list order.
    updated_by_id: dict[int, datetime] = {}
    usage_by_id: dict[int, float] = {}
    for s in candidates:
        sid = getattr(s, "id", None)
        if sid is None:
            continue
        updated_at = (
            _safe_dt(getattr(s, "updated_at", None))
            or _safe_dt(getattr(s, "created_at", None))
            or datetime.min
        )
        updated_by_id[int(sid)] = updated_at
        usage_by_id[int(sid)] = float(
            (getattr(s, "success_count", 0) or 0) + (getattr(s, "failure_count", 0) or 0)
        )

    sids_sorted = sorted(updated_by_id.keys())
    recency_norm_by_id: dict[int, float] = {}
    usage_norm_by_id: dict[int, float] = {}
    if sids_sorted:
        recency_ts_sorted = [updated_by_id[sid].timestamp() for sid in sids_sorted]
        rec_norm_sorted = _normalize(recency_ts_sorted)
        recency_norm_by_id = {sid: rec_norm_sorted[i] for i, sid in enumerate(sids_sorted)}

        usage_sorted = [usage_by_id.get(sid, 0.0) for sid in sids_sorted]
        usage_norm_sorted = _normalize(usage_sorted)
        usage_norm_by_id = {sid: usage_norm_sorted[i] for i, sid in enumerate(sids_sorted)}

    ranked: list[RankedSnippet] = []
    for s in candidates:
        echo_score = float(getattr(s, "echo_score", 0.0) or 0.0)

        haystack = f"{getattr(s, 'title', '')}\n{getattr(s, 'summary', '')}"
        keyword = _keyword_match_score(query=query, haystack=haystack)

        sid = int(getattr(s, "id", -1) or -1)
        usage = float(usage_norm_by_id.get(sid, 0.0)) if sid != -1 else 0.0
        recency = float(recency_norm_by_id.get(sid, 0.0)) if sid != -1 else 0.0

        score = (
            0.70 * echo_score
            + 0.20 * keyword
            + 0.05 * usage
            + 0.05 * recency
        )
        ranked.append(RankedSnippet(float(score), s))  # type: ignore[reportCallIssue]

    def _sort_key(r: RankedSnippet):
        s = r.snippet
        updated_at = _safe_dt(getattr(s, "updated_at", None)) or _safe_dt(getattr(s, "created_at", None)) or datetime.min
        sid = int(getattr(s, "id", -1) or -1)
        return (r.score, updated_at.timestamp(), sid)

    ranked.sort(key=_sort_key, reverse=True)
    return ranked
