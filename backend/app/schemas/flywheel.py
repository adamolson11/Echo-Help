from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.meta import Meta


class FlywheelRecommendRequest(BaseModel):
    problem: str = Field(min_length=1)


class FlywheelStep(BaseModel):
    id: str
    title: str
    instruction: str
    expected_signal: str


class FlywheelRecommendation(BaseModel):
    id: str
    title: str
    summary: str
    rationale: str
    source_label: str
    confidence: float | None = None
    ticket_id: int | None = None
    steps: list[FlywheelStep]


class FlywheelIssue(BaseModel):
    problem: str
    normalized_problem: str
    ask_echo_log_id: int
    answer: str
    mode: str | None = None
    confidence: float = 0.0
    source_count: int = 0
    top_ticket_id: int | None = None


class FlywheelState(BaseModel):
    id: Literal["input", "recommend", "execute", "capture", "store"]
    label: str
    status: Literal["complete", "current", "upcoming"]


class FlywheelContract(BaseModel):
    in_scope: list[str]
    deferred: list[str]
    acceptance_criteria: list[str]


class FlywheelRecommendResponse(BaseModel):
    meta: Meta = Meta(kind="flywheel_plan", version="v1")
    issue: FlywheelIssue
    states: list[FlywheelState]
    recommendations: list[FlywheelRecommendation]
    contract: FlywheelContract


class FlywheelOutcomeRequest(BaseModel):
    ask_echo_log_id: int
    problem: str = Field(min_length=1)
    recommendation_id: str = Field(min_length=1)
    recommendation_title: str = Field(min_length=1)
    ticket_id: int | None = None
    outcome_status: Literal["resolved", "needs_follow_up", "blocked"]
    completed_step_ids: list[str] = []
    execution_notes: str | None = None
    reusable_learning: str | None = None


class FlywheelSavedOutcome(BaseModel):
    ask_echo_feedback_id: int
    ticket_feedback_id: int | None = None
    helped: bool
    learning_summary: str


class FlywheelOutcomeResponse(BaseModel):
    meta: Meta = Meta(kind="flywheel_outcome", version="v1")
    saved: FlywheelSavedOutcome
    states: list[FlywheelState]
