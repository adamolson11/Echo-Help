from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, SQLModel


class SolutionSnippet(SQLModel, table=True):
    """A canonical solution snippet generated from ticket resolution or user feedback.

    Stored as Markdown (`content_md`) with a short plain-text `summary` and
    an `echo_score` indicating confidence/usefulness.
    """

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: int | None = Field(default=None, foreign_key="ticket.id")
    title: str
    summary: str | None = None
    content_md: str | None = Field(default=None, sa_column=Column(Text))
    source: str | None = None
    echo_score: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    tags: list[str] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SnippetFeedback(SQLModel, table=True):
    """Records user feedback about solution snippets.

    For simple feedback loops we store whether the snippet helped and an
    optional free-text `notes` field describing the actual fix.
    """

    id: int | None = Field(default=None, primary_key=True)
    snippet_id: int = Field(foreign_key="solutionsnippet.id")
    helped: bool
    notes: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeLink(SQLModel, table=True):
    """Optional lightweight link between snippets (placeholder for graph features)."""

    id: int | None = Field(default=None, primary_key=True)
    from_snippet_id: int = Field(foreign_key="solutionsnippet.id")
    to_snippet_id: int = Field(foreign_key="solutionsnippet.id")
    note: Optional[str] = None
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class SolutionSnippet(SQLModel, table=True):
    """A short, reusable solution extracted from a ticket or feedback.

    Stored snippets can be referenced by Ask Echo and tracked for
    effectiveness via success/failure counters and an echo_score.
    """

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: int | None = Field(default=None, foreign_key="ticket.id")
    summary: str | None = Field(default=None)
    snippet_text: str = Field(sa_column=Column(Text))
    echo_score: float = Field(default=0.0)
    success_count: int = Field(default=0)
    failure_count: int = Field(default=0)
    source: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SnippetFeedback(SQLModel, table=True):
    """Feedback entries tied to a snippet (e.g. user-provided confirmation)."""

    id: int | None = Field(default=None, primary_key=True)
    snippet_id: int = Field(foreign_key="solutionsnippet.id")
    ticket_id: int | None = Field(default=None, foreign_key="ticket.id")
    helpful: bool | None = Field(default=None)
    user_notes: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeLink(SQLModel, table=True):
    """Optional relation to link tickets/snippets (placeholder for later use)."""

    id: int | None = Field(default=None, primary_key=True)
    from_ticket_id: int | None = Field(default=None, foreign_key="ticket.id")
    to_ticket_id: int | None = Field(default=None, foreign_key="ticket.id")
    note: str | None = Field(default=None)
