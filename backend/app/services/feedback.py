from __future__ import annotations

import json
from typing import TypedDict

from sqlmodel import Session, select

from ..models.ask_echo_feedback import AskEchoFeedback
from ..models.ask_echo_log import AskEchoLog

LOW_CONFIDENCE_THRESHOLD = 0.35


class FeedbackAnalytics(TypedDict):
    answer_text: str
    source_count: int
    reasoning_summary: str
    low_confidence: bool
    no_sources: bool
    fallback_only: bool
    feedback_status: str
    feedback_rating: int


class FeedbackInspectionRecord(TypedDict):
    question: str
    answer: str
    confidence: float
    source_count: int
    sources: list[str]
    reasoning: str
    rating: int
    feedback_status: str
    feedback_notes: str | None
    selected_recommendation_id: str | None
    selected_recommendation_title: str | None
    outcome: str | None
    outcome_notes: str | None
    reusable_learning: str | None
    ask_echo_log_id: int
    created_at: str | None
    feedback_at: str | None
    low_confidence: bool
    no_sources: bool
    fallback_only: bool


def _normalize_answer(answer: str) -> str:
    """Normalize answer text only by collapsing repeated whitespace."""
    return " ".join((answer or "").split())


def normalize_sources(sources: list[str]) -> list[str]:
    """Deduplicate and whitespace-normalize source labels while preserving order."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in sources:
        source = " ".join((raw or "").split())
        if not source or source in seen:
            continue
        seen.add(source)
        normalized.append(source)
    return normalized


def _normalize_reasoning_summary(
    *,
    reasoning: str,
    low_confidence: bool,
    no_sources: bool,
    fallback_only: bool,
) -> str:
    base = (reasoning or "").strip() or "No reasoning summary available."
    if fallback_only and no_sources:
        return f"Fallback-only answer with no supporting sources. {base}"
    if fallback_only:
        return f"Fallback-only answer. {base}"
    if low_confidence:
        return f"Low-confidence answer. {base}"
    return base


def build_feedback_analytics(
    *,
    answer: str,
    confidence: float,
    sources: list[str],
    reasoning: str,
    mode: str,
) -> FeedbackAnalytics:
    normalized_sources = normalize_sources(sources)
    source_count = len(normalized_sources)
    low_confidence = float(confidence) < LOW_CONFIDENCE_THRESHOLD
    no_sources = source_count == 0
    fallback_only = mode == "general_answer" or no_sources
    return {
        "answer_text": _normalize_answer(answer),
        "source_count": source_count,
        "reasoning_summary": _normalize_reasoning_summary(
            reasoning=reasoning,
            low_confidence=low_confidence,
            no_sources=no_sources,
            fallback_only=fallback_only,
        ),
        "low_confidence": low_confidence,
        "no_sources": no_sources,
        "fallback_only": fallback_only,
        "feedback_status": "pending",
        "feedback_rating": 0,
    }


def apply_feedback_analytics(*, log: AskEchoLog, analytics: FeedbackAnalytics) -> None:
    log.answer_text = analytics["answer_text"]
    log.source_count = analytics["source_count"]
    log.reasoning_summary = analytics["reasoning_summary"]
    log.low_confidence = analytics["low_confidence"]
    log.no_sources = analytics["no_sources"]
    log.fallback_only = analytics["fallback_only"]
    log.feedback_status = analytics["feedback_status"]
    log.feedback_rating = analytics["feedback_rating"]


def apply_user_feedback(*, log: AskEchoLog, helped: bool) -> None:
    log.feedback_status = "helped" if helped else "not_helped"
    log.feedback_rating = 1 if helped else -1


def _load_reasoning_notes(reasoning_notes: str | None) -> dict[str, object]:
    if not reasoning_notes:
        return {}
    try:
        payload = json.loads(reasoning_notes)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_response_sources(log: AskEchoLog) -> list[str]:
    payload = _load_reasoning_notes(log.reasoning_notes)
    response = payload.get("response")
    if not isinstance(response, dict):
        return []
    raw_sources = response.get("sources")
    if not isinstance(raw_sources, list):
        return []
    return normalize_sources([str(source) for source in raw_sources if isinstance(source, str)])


def _extract_response_reasoning(log: AskEchoLog) -> str:
    payload = _load_reasoning_notes(log.reasoning_notes)
    response = payload.get("response")
    if not isinstance(response, dict):
        return ""
    reasoning = response.get("reasoning")
    return str(reasoning).strip() if isinstance(reasoning, str) else ""


def _extract_response_answer(log: AskEchoLog) -> str:
    payload = _load_reasoning_notes(log.reasoning_notes)
    response = payload.get("response")
    if not isinstance(response, dict):
        return ""
    answer = response.get("answer")
    return _normalize_answer(answer) if isinstance(answer, str) else ""


def _extract_latest_feedback_map(
    session: Session,
    *,
    log_ids: list[int],
) -> dict[int, AskEchoFeedback]:
    if not log_ids:
        return {}

    rows = list(
        session.exec(
            select(AskEchoFeedback)
            .where(AskEchoFeedback.ask_echo_log_id.in_(log_ids))  # type: ignore[attr-defined]
            .order_by(AskEchoFeedback.created_at.desc())  # type: ignore[attr-defined]
        ).all()
    )

    latest_by_log_id: dict[int, AskEchoFeedback] = {}
    for row in rows:
        latest_by_log_id.setdefault(int(row.ask_echo_log_id), row)
    return latest_by_log_id


def list_feedback_records(
    session: Session,
    *,
    limit: int = 100,
    low_confidence_only: bool = False,
) -> list[FeedbackInspectionRecord]:
    logs = list(
        session.exec(
            select(AskEchoLog)
            .order_by(AskEchoLog.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        ).all()
    )

    latest_feedback_by_log_id = _extract_latest_feedback_map(
        session,
        log_ids=[int(log.id) for log in logs if log.id is not None],
    )

    items: list[FeedbackInspectionRecord] = []
    for log in logs:
        if log.id is None:
            continue

        sources = _extract_response_sources(log)
        latest_feedback = latest_feedback_by_log_id.get(int(log.id))
        feedback_status = log.feedback_status or "pending"
        rating = int(log.feedback_rating or 0)
        feedback_notes = latest_feedback.notes if latest_feedback else None
        selected_recommendation_id = latest_feedback.selected_recommendation_id if latest_feedback else None
        selected_recommendation_title = latest_feedback.selected_recommendation_title if latest_feedback else None
        outcome = latest_feedback.outcome if latest_feedback else None
        outcome_notes = latest_feedback.outcome_notes if latest_feedback else None
        reusable_learning = latest_feedback.reusable_learning if latest_feedback else None
        feedback_at = latest_feedback.created_at.isoformat() if latest_feedback and latest_feedback.created_at else None
        if latest_feedback is not None:
            feedback_status = "helped" if latest_feedback.helped else "not_helped"
            rating = 1 if latest_feedback.helped else -1

        source_count = int(log.source_count or len(sources))
        answer_text = _normalize_answer(log.answer_text or _extract_response_answer(log))
        computed_low_confidence = bool(
            log.low_confidence or float(log.kb_confidence or 0.0) < LOW_CONFIDENCE_THRESHOLD
        )
        computed_no_sources = bool(log.no_sources or source_count == 0)
        computed_fallback_only = bool(log.fallback_only or computed_no_sources or log.mode == "general_answer")
        reasoning_summary = (
            log.reasoning_summary
            or _normalize_reasoning_summary(
                reasoning=_extract_response_reasoning(log),
                low_confidence=computed_low_confidence,
                no_sources=computed_no_sources,
                fallback_only=computed_fallback_only,
            )
        ).strip()
        low_confidence = computed_low_confidence
        no_sources = computed_no_sources
        fallback_only = computed_fallback_only

        if low_confidence_only and not low_confidence:
            continue

        items.append(
            FeedbackInspectionRecord(
                ask_echo_log_id=int(log.id),
                question=log.query,
                answer=answer_text,
                confidence=float(log.kb_confidence or 0.0),
                source_count=source_count,
                sources=sources,
                reasoning=reasoning_summary,
                rating=rating,
                feedback_status=feedback_status,
                feedback_notes=feedback_notes,
                selected_recommendation_id=selected_recommendation_id,
                selected_recommendation_title=selected_recommendation_title,
                outcome=outcome,
                outcome_notes=outcome_notes,
                reusable_learning=reusable_learning,
                created_at=log.created_at.isoformat() if log.created_at else None,
                feedback_at=feedback_at,
                low_confidence=low_confidence,
                no_sources=no_sources,
                fallback_only=fallback_only,
            )
        )

    return items
