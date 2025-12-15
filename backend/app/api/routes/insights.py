from __future__ import annotations

# ruff: noqa: B008
from fastapi import APIRouter, Depends
from sklearn.cluster import KMeans
from sqlmodel import Session, select
from sqlalchemy import desc

from ...db import get_session
from ...models.ask_echo_log import AskEchoLog
from ...models.ticket_feedback import TicketFeedback
from ...schemas.insights import (
    AskEchoFeedbackResponse,
    AskEchoLogsResponse,
    FeedbackCluster,
    FeedbackClustersResponse,
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


@router.get("/pattern-radar")
def get_pattern_radar(
    session: Session = Depends(get_session),
) -> dict:
    """Return snippet-based pattern radar stats (backwards compatible)."""
    return get_snippet_pattern_radar(session)


@router.get("/ticket-pattern-radar")
def get_ticket_pattern_radar(
    days: int = 14,
    session: Session = Depends(get_session),
) -> dict:
    """Return basic ticket pattern stats for the last ``days`` days."""
    return extract_ticket_patterns(session, days=days)


@router.get("/ask-echo-logs", response_model=AskEchoLogsResponse)
def get_ask_echo_logs(limit: int = 50, session: Session = Depends(get_session)) -> AskEchoLogsResponse:
    stmt = select(AskEchoLog).order_by(desc(AskEchoLog.created_at)).limit(limit)
    rows = session.exec(stmt).all()
    # Keep response stable and JSON-friendly without leaking ORM internals.
    items = [r.model_dump() for r in rows]
    return AskEchoLogsResponse(items=items)


@router.get("/ask-echo-feedback", response_model=AskEchoFeedbackResponse)
def get_ask_echo_feedback(
    limit: int = 100,
    helped: bool | None = None,
    session: Session = Depends(get_session),
):
    """Return recent ticket feedback rows. This endpoint is primarily used by the Insights UI.

    Optionally filter by `helped` (true/false). Results are ordered newest-first.
    """
    query = select(TicketFeedback)
    if helped is not None:
        query = query.where(TicketFeedback.helped == helped)

    query = query.order_by(desc(TicketFeedback.created_at)).limit(limit)
    rows = session.exec(query).all()
    items = [TicketFeedbackRead.model_validate(r).model_dump() for r in rows]
    return AskEchoFeedbackResponse(items=items)
