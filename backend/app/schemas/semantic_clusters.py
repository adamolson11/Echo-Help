from __future__ import annotations

from sqlmodel import SQLModel


class SemanticClusterTicket(SQLModel):
    ticket_id: int
    summary: str | None = None
    description: str | None = None
    score: float | None = None


class SemanticCluster(SQLModel):
    cluster_index: int
    label: str | None = None
    size: int
    tickets: list[SemanticClusterTicket]


class SemanticClustersRequest(SQLModel):
    n_clusters: int = 5
    max_examples: int = 3
