from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.meta import Meta

StageName = Literal[
    "command_received",
    "agent_passes_completed",
    "outputs_cleaned",
    "workflow_generated",
    "work_executed",
    "outcomes_archived",
    "next_cycle_prepared",
    "failed",
]


class OrchestrationAgentSpec(BaseModel):
    name: str
    role: str
    focus: list[str] = Field(default_factory=list)


class OrchestrationCycleCreate(BaseModel):
    command: str
    agents: list[OrchestrationAgentSpec]
    archive_seed: list[str] = Field(default_factory=list)
    seed_cycle_id: int | None = None


class OrchestrationAgentPassRead(BaseModel):
    agent_name: str
    role: str
    pass_index: int = 1
    status: Literal["completed"] = "completed"
    format_version: Literal["v1"] = "v1"
    findings: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    summary: str


class OrchestrationCleanedOutput(BaseModel):
    findings: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    archive_seed: list[str] = Field(default_factory=list)


class OrchestrationWorkflowTask(BaseModel):
    task_id: str
    title: str
    source_agents: list[str] = Field(default_factory=list)
    status: Literal["planned"] = "planned"


class OrchestrationWorkflow(BaseModel):
    generated_from: Literal["cleaned_output"] = "cleaned_output"
    items: list[OrchestrationWorkflowTask] = Field(default_factory=list)


class OrchestrationExecutionOutcome(BaseModel):
    task_id: str
    status: Literal["completed"] = "completed"
    result: str


class OrchestrationStageTransition(BaseModel):
    stage: StageName
    status: Literal["completed", "failed"] = "completed"
    detail: str
    occurred_at: datetime


class OrchestrationRetryPolicy(BaseModel):
    retryable_stages: list[StageName] = Field(
        default_factory=lambda: [
            "agent_passes_completed",
            "outputs_cleaned",
            "workflow_generated",
            "work_executed",
            "outcomes_archived",
            "next_cycle_prepared",
        ]
    )
    rule: str = "Retry resumes from the first incomplete stage and never reruns completed agent passes."


class OrchestrationArchive(BaseModel):
    cleaned_output: OrchestrationCleanedOutput
    daily_workflow: OrchestrationWorkflow
    execution_outcomes: list[OrchestrationExecutionOutcome] = Field(default_factory=list)
    next_cycle_seed: list[str] = Field(default_factory=list)


class OrchestrationCycleResponse(BaseModel):
    meta: Meta = Meta(kind="orchestration_cycle", version="v1")
    cycle_id: int
    status: Literal["completed", "failed"]
    current_stage: StageName
    command: str
    seeded_from_cycle_id: int | None = None
    agent_passes: list[OrchestrationAgentPassRead] = Field(default_factory=list)
    cleaned_output: OrchestrationCleanedOutput
    daily_workflow: OrchestrationWorkflow
    execution_outcomes: list[OrchestrationExecutionOutcome] = Field(default_factory=list)
    archive: OrchestrationArchive
    next_cycle_seed: list[str] = Field(default_factory=list)
    stage_history: list[OrchestrationStageTransition] = Field(default_factory=list)
    retry_policy: OrchestrationRetryPolicy = Field(default_factory=OrchestrationRetryPolicy)
