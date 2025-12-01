from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


class Ticket(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    short_id: str | None = Field(
        default=None, sa_column=Column("short_id", Text, unique=True)
    )
    external_key: str
    source: str
    project_key: str
    summary: str
    description: str
    # A Markdown body for knowledge-base style content
    body_md: str | None = Field(default=None, sa_column=Column(Text))
    root_cause: str | None = Field(default=None, sa_column=Column(Text))
    environment: str | None = None
    # Tags stored as JSON array for flexibility
    tags: list[str] | None = Field(default=None, sa_column=Column(JSON))
    status: str
    priority: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None


class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str


class Subcategory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="category.id")
    name: str
