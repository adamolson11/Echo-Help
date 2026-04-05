from __future__ import annotations

# ruff: noqa: B008
import logging
from typing import Any

try:
    import numpy as np
except ModuleNotFoundError:
    np = None  # type: ignore[assignment]
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models.embedding import Embedding
from ..models.ticket import Ticket
from ..schemas.semantic_clusters import (
    SemanticCluster,
    SemanticClustersRequest,
    SemanticClusterTicket,
)

router = APIRouter(
    prefix="/insights",
    tags=["insights"],
)

_LOG = logging.getLogger(__name__)


def _kmeans_numpy(
    matrix: Any,
    n_clusters: int,
    max_iter: int = 100,
    rng: Any | None = None,
):
    """
    Simple KMeans implementation using numpy. Returns labels and centroids.
    """
    assert np is not None
    if rng is None:
        rng = np.random.default_rng()

    n_samples, dim = matrix.shape
    # choose initial centroids as random samples
    indices = rng.choice(n_samples, size=n_clusters, replace=False)
    centroids = matrix[indices].astype(float)

    labels = np.zeros(n_samples, dtype=int)

    for _ in range(max_iter):
        # assign labels
        dists = np.linalg.norm(matrix[:, None, :] - centroids[None, :, :], axis=2)
        new_labels = np.argmin(dists, axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        # recompute centroids
        for k in range(n_clusters):
            members = matrix[labels == k]
            if len(members) == 0:
                # reinitialize empty centroid
                centroids[k] = matrix[rng.choice(n_samples)]
            else:
                centroids[k] = members.mean(axis=0)

    return labels, centroids


@router.post("/semantic-clusters", response_model=list[SemanticCluster])
def semantic_clusters(
    body: SemanticClustersRequest = Depends(), session: Session = Depends(get_session)
) -> list[SemanticCluster]:
    if np is None:
        _LOG.warning("Semantic clustering disabled: numpy not installed")
        return []
    assert np is not None

    n_clusters = max(1, int(body.n_clusters))
    max_examples = max(1, int(body.max_examples))

    # load embeddings associated with tickets
    emb_rows = list(
        session.exec(select(Embedding).where(Embedding.ticket_id.is_not(None)))  # type: ignore[reportAttributeAccessIssue]
    )
    if not emb_rows:
        return []

    # Filter out any rows where vector is missing or malformed
    items = [
        e for e in emb_rows if isinstance(e.vector, (list, tuple)) and len(e.vector) > 0
    ]
    if not items:
        return []

    matrix = np.asarray([e.vector for e in items], dtype=float)
    n_clusters = min(n_clusters, len(items))

    # prefer sklearn KMeans if available for better defaults
    try:
        from sklearn.cluster import KMeans  # type: ignore

        kmeans = KMeans(n_clusters=n_clusters, n_init="auto")
        labels = kmeans.fit_predict(matrix)
        centroids = kmeans.cluster_centers_
    except Exception:
        labels, centroids = _kmeans_numpy(matrix, n_clusters)

    clusters: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(int(label), []).append(idx)

    results: list[SemanticCluster] = []

    for cluster_idx, indices in clusters.items():
        # compute distances to centroid and pick closest examples
        centroid = centroids[int(cluster_idx)]
        dists = np.linalg.norm(matrix[indices] - centroid, axis=1)
        order = np.argsort(dists)[:max_examples]
        example_indices = [indices[i] for i in order]

        tickets: list[SemanticClusterTicket] = []
        for pos_idx, global_i in enumerate(example_indices):
            emb = items[int(global_i)]
            ticket = session.get(Ticket, emb.ticket_id)
            if ticket is None:
                continue
            if ticket.id is None:
                continue
            dist_val = float(dists[pos_idx]) if pos_idx < len(dists) else None
            tickets.append(
                SemanticClusterTicket(
                    ticket_id=ticket.id,
                    summary=ticket.summary,
                    description=ticket.description,
                    score=dist_val,
                )
            )

        label = None
        if tickets:
            label = tickets[0].summary

        results.append(
            SemanticCluster(
                cluster_index=int(cluster_idx),
                label=label,
                size=len(indices),
                tickets=tickets,
            )
        )

    # sort clusters by size desc
    results.sort(key=lambda c: c.size, reverse=True)

    return results
