from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from backend.app.core.time import utcnow


class OrchestrationCycle(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    command: str = Field(index=True)
    status: str = Field(default="running", index=True)
    current_stage: str = Field(default="command_received", index=True)
    seeded_from_cycle_id: int | None = Field(default=None, foreign_key="orchestrationcycle.id")
    request_payload_json: str = Field(sa_column=Column(Text, nullable=False))
    archive_seed_json: str | None = Field(default=None, sa_column=Column(Text))
    cleaned_output_json: str | None = Field(default=None, sa_column=Column(Text))
    daily_workflow_json: str | None = Field(default=None, sa_column=Column(Text))
    execution_outcomes_json: str | None = Field(default=None, sa_column=Column(Text))
    archive_json: str | None = Field(default=None, sa_column=Column(Text))
    next_cycle_seed_json: str | None = Field(default=None, sa_column=Column(Text))
    stage_history_json: str | None = Field(default=None, sa_column=Column(Text))
    retry_policy_json: str | None = Field(default=None, sa_column=Column(Text))
    failure_reason: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow, index=True)
