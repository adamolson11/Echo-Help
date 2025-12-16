from __future__ import annotations

# ruff: noqa: B008
from fastapi import APIRouter, Depends
from sklearn.cluster import KMeans
from sqlmodel import Session, select
import json
from fastapi import HTTPException

from ...db import get_session
from ...models.ask_echo_log import AskEchoLog
from ...models.ask_echo_feedback import AskEchoFeedback
from ...models.ticket_feedback import TicketFeedback
from ...schemas.insights import (
    AskEchoFeedbackResponse,
    AskEchoFeedbackRow,
    AskEchoLogDetail,
    AskEchoLogDetailResponse,
    AskEchoLogReasoning,
    AskEchoLogsResponse,
    AskEchoLogSummary,
    FeedbackCluster,
    FeedbackClustersResponse,
    PatternRadarResponse,
    ReasoningSnippetCandidate,
    TicketPatternRadarResponse,
    TicketFeedbackInsights,
    UnhelpfulExample,
)
from ...schemas.ticket_feedback import TicketFeedbackRead
from ...services.embeddings import embed_text
from ...services.pattern_radar import extract_ticket_patterns, get_snippet_pattern_radar

router = APIRouter(
    prefix="/insights",
    tags=["insights"],
)


@router.get("/feedback", response_model=TicketFeedbackInsights)
def get_ticket_feedback_insights(
    limit_unhelpful_examples: int = 10,
    session: Session = Depends(get_session),
) -> TicketFeedbackInsights:
    query = select(TicketFeedback)
    feedback_items: list[TicketFeedback] = list(session.exec(query).all())

    total = len(feedback_items)
    helped_true = sum(1 for f in feedback_items if f.helped is True)
    helped_false = sum(1 for f in feedback_items if f.helped is False)
    helped_null = sum(1 for f in feedback_items if f.helped is None)

    unhelpful = [
        UnhelpfulExample(
            ticket_id=f.ticket_id,
            resolution_notes=f.resolution_notes,
            created_at=f.created_at,
        )
        for f in feedback_items
        if f.helped is False
    ]

    # Most recent first
    unhelpful.sort(key=lambda x: x.created_at, reverse=True)
    unhelpful = unhelpful[:limit_unhelpful_examples]

    return TicketFeedbackInsights(
        total_feedback=total,
        helped_true=helped_true,
        helped_false=helped_false,
        helped_null=helped_null,
        unhelpful_examples=unhelpful,
    )


# --- Feedback Clustering Endpoint ---
@router.get("/feedback/clusters", response_model=FeedbackClustersResponse)
def get_ticket_feedback_clusters(
    n_clusters: int = 5,
    max_examples_per_cluster: int = 3,
    session: Session = Depends(get_session),
) -> FeedbackClustersResponse:
    # 1. Load feedback with non-empty resolution_notes
    query = select(TicketFeedback).where(
        TicketFeedback.resolution_notes.is_not(None)  # type: ignore[reportAttributeAccessIssue]
    )
    feedback_items: list[TicketFeedback] = list(session.exec(query).all())

    if not feedback_items:
        return FeedbackClustersResponse(clusters=[])

    texts = [
        f.resolution_notes.strip()
        for f in feedback_items
        if f.resolution_notes and f.resolution_notes.strip()
    ]
    items = [
        f for f in feedback_items if f.resolution_notes and f.resolution_notes.strip()
    ]

    if not items:
        return FeedbackClustersResponse(clusters=[])

    n_clusters = max(1, min(n_clusters, len(items)))

    # 2. Embed notes
    embeddings = embed_text(texts)  # -> List[List[float]]

    # 3. Cluster with KMeans
    kmeans = KMeans(n_clusters=n_clusters, n_init="auto")
    labels = kmeans.fit_predict(embeddings)

    # 4. Group into clusters
    clusters: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(int(label), []).append(idx)

    results: list[FeedbackCluster] = []

    for cluster_idx, indices in clusters.items():
        # sort by recency (most recent first)
        indices_sorted = sorted(
            indices,
            key=lambda i: items[i].created_at,
            reverse=True,
        )

        example_indices = indices_sorted[:max_examples_per_cluster]
        example_ticket_ids = [items[i].ticket_id for i in example_indices]
        example_notes = [texts[i] for i in example_indices]

        results.append(
            FeedbackCluster(
                cluster_index=int(cluster_idx),
                size=len(indices),
                example_ticket_ids=example_ticket_ids,
                example_notes=example_notes,
            )
        )

    # sort clusters by size desc
    results.sort(key=lambda c: c.size, reverse=True)

    return FeedbackClustersResponse(clusters=results)


@router.get("/pattern-radar", response_model=PatternRadarResponse)
def get_pattern_radar(
    session: Session = Depends(get_session),
) -> dict:
    """Return snippet-based pattern radar stats (backwards compatible)."""
    return get_snippet_pattern_radar(session)


@router.get("/ticket-pattern-radar", response_model=TicketPatternRadarResponse)
def get_ticket_pattern_radar(
    days: int = 14,
    session: Session = Depends(get_session),
) -> dict:
    """Return basic ticket pattern stats for the last ``days`` days."""
    return extract_ticket_patterns(session, days=days)


@router.get("/ask-echo-logs", response_model=AskEchoLogsResponse)
def get_ask_echo_logs(limit: int = 50, session: Session = Depends(get_session)) -> AskEchoLogsResponse:
    stmt = select(AskEchoLog).order_by(AskEchoLog.created_at.desc()).limit(limit)  # type: ignore[attr-defined]
    rows = session.exec(stmt).all()
    # Keep response stable and JSON-friendly without leaking ORM internals.
    items = [
        AskEchoLogSummary(
            id=r.id or 0,
            query_text=r.query,
            ticket_id=None,
            echo_score=r.echo_score,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
        if r.id is not None
    ]
    return AskEchoLogsResponse(items=items)


@router.get("/ask-echo-logs/{log_id}", response_model=AskEchoLogDetailResponse)
def get_ask_echo_log_detail(
    log_id: int,
    session: Session = Depends(get_session),
) -> AskEchoLogDetailResponse:
    """Return Ask Echo log detail (Insights contract).

    This lives under /insights so the Insights UI can use a single, meta-enveloped
    API surface for log list + detail.
    """
    log = session.get(AskEchoLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="AskEchoLog not found")

    try:
        candidate_json = log.candidate_snippet_ids_json or "[]"
        candidate_data = json.loads(candidate_json)
    except json.JSONDecodeError:
        candidate_data = []

    try:
        chosen_json = log.chosen_snippet_ids_json or "[]"
        chosen_ids = json.loads(chosen_json)
    except json.JSONDecodeError:
        chosen_ids = []

    norm_candidates = []
    for item in candidate_data:
        if not isinstance(item, dict):
            continue
        cid = item.get("id")
        score = item.get("score")
        title = item.get("title")
        if cid is None:
            continue
        norm_candidates.append(
            ReasoningSnippetCandidate(
                id=int(cid),
                title=str(title) if isinstance(title, str) else None,
                score=float(score) if isinstance(score, (int, float)) else None,
            )
        )

    chosen_ids_norm: list[int] = []
    if isinstance(chosen_ids, list):
        for v in chosen_ids:
            if isinstance(v, int):
                chosen_ids_norm.append(v)
            elif isinstance(v, str) and v.isdigit():
                chosen_ids_norm.append(int(v))

    reasoning = AskEchoLogReasoning(
        candidate_snippets=norm_candidates,
        chosen_snippet_ids=chosen_ids_norm,
    )

    return AskEchoLogDetailResponse(
        item=AskEchoLogDetail(
            id=log.id or 0,
            query_text=log.query,
            answer_text="",
            ticket_id=None,
            echo_score=log.echo_score,
            created_at=log.created_at.isoformat() if log.created_at else None,
            reasoning=reasoning,
            reasoning_notes=log.reasoning_notes,
        )
    )


@router.get("/ask-echo-feedback", response_model=AskEchoFeedbackResponse)
def get_ask_echo_feedback(
    limit: int = 100,
    helped: bool | None = None,
    session: Session = Depends(get_session),
):
    """Return recent Ask Echo feedback rows.

    This is answer-level feedback keyed by `ask_echo_log_id`. We also attach
    `query_text` from the associated AskEchoLog for UI display.
    """
    query = select(AskEchoFeedback)
    if helped is not None:
        query = query.where(AskEchoFeedback.helped == helped)

    query = query.order_by(AskEchoFeedback.created_at.desc()).limit(limit)  # type: ignore[attr-defined]
    rows = list(session.exec(query).all())

    # Avoid N+1 queries: bulk load logs for the returned feedback rows.
    log_ids = {r.ask_echo_log_id for r in rows}
    logs_by_id: dict[int, AskEchoLog] = {}
    if log_ids:
        stmt = select(AskEchoLog).where(AskEchoLog.id.in_(log_ids))  # type: ignore[attr-defined]
        logs = list(session.exec(stmt).all())
        logs_by_id = {int(l.id): l for l in logs if l.id is not None}

    items: list[AskEchoFeedbackRow] = []
    for r in rows:
        log = logs_by_id.get(int(r.ask_echo_log_id))
        items.append(
            AskEchoFeedbackRow(
                id=r.id or 0,
                ask_echo_log_id=r.ask_echo_log_id,
                helped=r.helped,
                notes=r.notes,
                query_text=(log.query if log else None),
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
        )

    return AskEchoFeedbackResponse(items=items)
