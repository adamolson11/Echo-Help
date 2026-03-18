from __future__ import annotations

import re
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
    signals: dict[str, object] | None = None


@dataclass(frozen=True)
class RankedSnippet:
    score: float
    snippet: SolutionSnippet


def clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def _safe_dt(value: datetime | None) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if token
    }


def _keyword_match_score(*, query: str, haystack: str) -> float:
    normalized_query = (query or "").strip().lower()
    if not normalized_query:
        return 0.0
    query_tokens = _tokenize(normalized_query)
    if not query_tokens:
        return 0.0

    haystack_text = haystack or ""
    haystack_tokens = _tokenize(haystack_text)
    if not haystack_tokens:
        return 0.0

    overlap = len(query_tokens & haystack_tokens) / float(len(query_tokens))
    phrase_match = 1.0 if normalized_query in haystack_text.lower() else 0.0
    return clamp01((0.7 * overlap) + (0.3 * phrase_match))


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi <= lo:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _parse_tags(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    out: set[str] = set()
    for item in value:
        if isinstance(item, str):
            out.add(item.strip().lower())
    return out


def _query_env_hint(query: str) -> str | None:
    q = (query or "").strip().lower()
    if not q:
        return None
    if any(tok in q for tok in ("prod", "production", "live")):
        return "prod"
    if any(tok in q for tok in ("stage", "staging", "preprod")):
        return "stage"
    if any(tok in q for tok in ("local", "dev", "developer")):
        return "local"
    return None


def _query_severity_hint(query: str) -> str | None:
    q = (query or "").strip().lower()
    if not q:
        return None
    if "sev1" in q or "critical" in q:
        return "sev1"
    if "sev2" in q or "high" in q:
        return "sev2"
    if "sev3" in q or "medium" in q:
        return "sev3"
    if "sev4" in q or "low" in q:
        return "sev4"
    p = re.search(r"\bp([1-4])\b", q)
    if p:
        return f"sev{p.group(1)}"
    return None


def _ticket_fix_confirmed(ticket: Ticket) -> float:
    if getattr(ticket, "fix_confirmed_good", None) is True:
        return 1.0
    if getattr(ticket, "fix_confirmed_good", None) is False:
        return 0.0
    tags = _parse_tags(getattr(ticket, "tags", None))
    if "fix_confirmed:true" in tags:
        return 1.0
    status = str(getattr(ticket, "status", "") or "").strip().lower()
    if status in {"closed", "resolved", "done"} and getattr(ticket, "resolved_at", None) is not None:
        return 1.0
    return 0.0


def _ticket_env_match(*, ticket: Ticket, query: str) -> float:
    hint = _query_env_hint(query)
    if hint is None:
        return 0.0
    env = str(getattr(ticket, "environment", "") or "").strip().lower()
    return 1.0 if env == hint else 0.0


def _ticket_severity_match(*, ticket: Ticket, query: str) -> float:
    hint = _query_severity_hint(query)
    if hint is None:
        return 0.0

    tags = _parse_tags(getattr(ticket, "tags", None))
    for tag in tags:
        if tag.startswith("severity:"):
            return 1.0 if tag.split(":", 1)[1] == hint else 0.0

    priority = str(getattr(ticket, "priority", "") or "").strip().lower()
    if priority in {"p1", "p2", "p3", "p4"}:
        return 1.0 if priority.replace("p", "sev") == hint else 0.0
    return 0.0


def _ticket_answer_quality_label(ticket: Ticket) -> str:
    label = str(getattr(ticket, "answer_quality_label", "") or "").strip().lower()
    if label in {"good", "bad", "mixed"}:
        return label

    tags = _parse_tags(getattr(ticket, "tags", None))
    if "answer_quality:good" in tags:
        return "good"
    if "answer_quality:bad" in tags:
        return "bad"
    if "answer_quality:mixed" in tags:
        return "mixed"
    return "mixed"


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


def calculate_kb_confidence(
    *,
    kb_backed: bool,
    top_snippet_echo_score: float | None,
    top_ticket_score: float,
    has_snippets: bool,
    has_tickets: bool,
    semantic_similarity: float | None = None,
    keyword_overlap: float | None = None,
    recency: float | None = None,
) -> float:
    """Blend the best available retrieval signals into a bounded confidence."""
    if not kb_backed:
        return 0.0

    if has_snippets and top_snippet_echo_score is not None:
        base_confidence = clamp01(float(top_snippet_echo_score))
    elif has_tickets:
        base_confidence = clamp01(float(top_ticket_score or 0.0))
    else:
        base_confidence = 0.0

    signal_values = [
        clamp01(float(value))
        for value in (semantic_similarity, keyword_overlap, recency)
        if value is not None
    ]
    if not signal_values:
        return base_confidence

    signal_average = sum(signal_values) / float(len(signal_values))
    return clamp01((0.85 * base_confidence) + (0.15 * signal_average))


def rank_tickets(
    session: Session,
    *,
    candidates: list[Ticket],
    query: str,
    semantic_scores: dict[int, float] | None = None,
    use_learning_lite: bool = True,
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
        fix_confirmed = _ticket_fix_confirmed(t)
        env_match = _ticket_env_match(ticket=t, query=query)
        severity_match = _ticket_severity_match(ticket=t, query=query)
        quality_label = _ticket_answer_quality_label(t)
        bad_quality_penalty = 1.0 if quality_label == "bad" else 0.4 if quality_label == "mixed" else 0.0

        boosts_applied: list[str] = []
        if fix_confirmed > 0.0:
            boosts_applied.append("fix_confirmed")
        if env_match > 0.0:
            boosts_applied.append("env_match")
        if severity_match > 0.0:
            boosts_applied.append("severity_match")
        if bad_quality_penalty > 0.0:
            boosts_applied.append("bad_quality_penalty")

        # Weights are intentionally simple and explicit (no hidden heuristics).
        # Weighted retrieval (learning-lite): semantic + recency + success + env + severity.
        if use_learning_lite:
            score = (
                0.48 * semantic
                + 0.18 * keyword
                + 0.10 * feedback
                + 0.05 * usage
                + 0.05 * recency
                + 0.08 * fix_confirmed
                + 0.04 * env_match
                + 0.02 * severity_match
                - 0.12 * bad_quality_penalty
            )
        else:
            score = (
                0.55 * semantic
                + 0.25 * keyword
                + 0.10 * feedback
                + 0.05 * usage
                + 0.05 * recency
            )

        ranked.append(
            RankedTicket(
                float(score),
                t,
                signals={
                    "semantic": float(semantic),
                    "keyword": float(keyword),
                    "feedback": float(feedback),
                    "usage": float(usage),
                    "recency": float(recency),
                    "fix_confirmed": float(fix_confirmed),
                    "env_match": float(env_match),
                    "severity_match": float(severity_match),
                    "bad_quality_penalty": float(bad_quality_penalty),
                    "answer_quality_label": quality_label,
                    "boosts_applied": boosts_applied,
                    "final_score": float(score),
                },
            )
        )

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
