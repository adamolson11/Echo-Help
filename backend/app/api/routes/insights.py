from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from backend.app.db import get_session
from backend.app.models.ticket_feedback import TicketFeedback
from backend.app.schemas.insights import (
    TicketFeedbackInsights,
    UnhelpfulExample,
    FeedbackCluster,
)

from sklearn.cluster import KMeans
from backend.app.services.embeddings import embed_text

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
    feedback_items: List[TicketFeedback] = session.exec(query).all()

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
@router.get("/feedback/clusters", response_model=List[FeedbackCluster])
def get_ticket_feedback_clusters(
    n_clusters: int = 5,
    max_examples_per_cluster: int = 3,
    session: Session = Depends(get_session),
) -> List[FeedbackCluster]:
    # 1. Load feedback with non-empty resolution_notes
    query = select(TicketFeedback).where(TicketFeedback.resolution_notes.is_not(None))
    feedback_items: List[TicketFeedback] = session.exec(query).all()

    if not feedback_items:
        return []

    texts = [f.resolution_notes.strip() for f in feedback_items if f.resolution_notes and f.resolution_notes.strip()]
    items = [f for f in feedback_items if f.resolution_notes and f.resolution_notes.strip()]

    if not items:
        return []

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

    results: List[FeedbackCluster] = []

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

    return results
