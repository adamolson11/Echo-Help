from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel

from backend.app.core.time import utcnow


class Ticket(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    key: str | None = Field(default=None, sa_column=Column("key", Text))
    short_id: str | None = Field(
        default=None, sa_column=Column("short_id", Text, unique=True)
    )
    external_key: str
    source: str
    source_system: str | None = None
    source_id: str | None = None
    source_url: str | None = Field(default=None, sa_column=Column(Text))
    project_key: str
    summary: str
    description: str
    product_area: str | None = None
    # A Markdown body for knowledge-base style content
    body_md: str | None = Field(default=None, sa_column=Column(Text))
    root_cause: str | None = Field(default=None, sa_column=Column(Text))
    root_cause_good: str | None = Field(default=None, sa_column=Column(Text))
    root_cause_bad: str | None = Field(default=None, sa_column=Column(Text))
    bad_reason: str | None = Field(default=None, sa_column=Column(Text))
    environment: str | None = None
    severity: str | None = None
    # Tags stored as JSON array for flexibility
    tags: list[str] | None = Field(default=None, sa_column=Column(JSON))
    repro_steps: list[str] | None = Field(default=None, sa_column=Column(JSON))
    expected_result: str | None = Field(default=None, sa_column=Column(Text))
    actual_result: str | None = Field(default=None, sa_column=Column(Text))
    resolution_good: list[str] | None = Field(default=None, sa_column=Column(JSON))
    fix_confirmed_good: bool | None = None
    resolution_bad: list[str] | None = Field(default=None, sa_column=Column(JSON))
    answer_quality_label: str | None = None
    status: str
    priority: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None


class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str


class Subcategory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="category.id")
    name: str
