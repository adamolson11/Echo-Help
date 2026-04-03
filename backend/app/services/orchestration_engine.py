from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypeVar, cast

from pydantic import BaseModel
from sqlmodel import Session, col, select

from backend.app.core.time import utcnow
from backend.app.models.orchestration_agent_pass import OrchestrationAgentPass
from backend.app.models.orchestration_cycle import OrchestrationCycle
from backend.app.schemas.orchestration import (
    OrchestrationAgentPassRead,
    OrchestrationArchive,
    OrchestrationCleanedOutput,
    OrchestrationCycleResponse,
    OrchestrationExecutionOutcome,
    OrchestrationRetryPolicy,
    OrchestrationStageTransition,
    OrchestrationWorkflow,
    OrchestrationWorkflowTask,
    StageName,
)

STAGE_SEQUENCE = [
    "command_received",
    "agent_passes_completed",
    "outputs_cleaned",
    "workflow_generated",
    "work_executed",
    "outcomes_archived",
    "next_cycle_prepared",
]


@dataclass(frozen=True)
class OrchestrationAgentRequest:
    name: str
    role: str
    focus: tuple[str, ...]


@dataclass(frozen=True)
class OrchestrationEngineRequest:
    command: str
    agents: tuple[OrchestrationAgentRequest, ...]
    archive_seed: tuple[str, ...] = ()
    seeded_from_cycle_id: int | None = None


def execute_orchestration_cycle(
    *, session: Session, req: OrchestrationEngineRequest
) -> OrchestrationCycleResponse:
    command = _normalize_text(req.command)
    if not command:
        raise ValueError("command is required")
    if not req.agents:
        raise ValueError("at least one agent is required")

    prior_seed = _load_prior_seed(session=session, cycle_id=req.seeded_from_cycle_id)
    archive_seed = _stable_dedupe([*prior_seed, *req.archive_seed])
    retry_policy = OrchestrationRetryPolicy()

    cycle = OrchestrationCycle(
        command=command,
        request_payload_json=json.dumps(
            {
                "command": command,
                "agents": [
                    {"name": agent.name, "role": agent.role, "focus": list(agent.focus)}
                    for agent in req.agents
                ],
            }
        ),
        archive_seed_json=_dump_json(archive_seed),
        retry_policy_json=_dump_model(retry_policy),
        seeded_from_cycle_id=req.seeded_from_cycle_id,
    )
    session.add(cycle)
    session.commit()
    session.refresh(cycle)

    stage_history: list[OrchestrationStageTransition] = []
    _record_stage(
        session=session,
        cycle=cycle,
        stage_history=stage_history,
        stage="command_received",
        detail="Accepted command and created a persisted orchestration cycle.",
    )

    try:
        agent_passes = [_build_agent_pass(command=command, archive_seed=archive_seed, agent=agent) for agent in req.agents]
        for agent_pass in agent_passes:
            session.add(
                OrchestrationAgentPass(
                    cycle_id=cycle.id or 0,
                    agent_name=agent_pass.agent_name,
                    role=agent_pass.role,
                    pass_index=agent_pass.pass_index,
                    status=agent_pass.status,
                    response_json=_dump_model(agent_pass),
                )
            )
        session.commit()
        _record_stage(
            session=session,
            cycle=cycle,
            stage_history=stage_history,
            stage="agent_passes_completed",
            detail=f"Executed {len(agent_passes)} deterministic agent passes.",
        )

        cleaned_output = _clean_agent_outputs(agent_passes=agent_passes, archive_seed=archive_seed)
        cycle.cleaned_output_json = _dump_model(cleaned_output)
        _record_stage(
            session=session,
            cycle=cycle,
            stage_history=stage_history,
            stage="outputs_cleaned",
            detail="Normalized and deduplicated findings, actions, and archive inputs.",
        )

        workflow = _build_daily_workflow(agent_passes=agent_passes, cleaned_output=cleaned_output)
        cycle.daily_workflow_json = _dump_model(workflow)
        _record_stage(
            session=session,
            cycle=cycle,
            stage_history=stage_history,
            stage="workflow_generated",
            detail=f"Generated {len(workflow.items)} daily workflow tasks from cleaned output only.",
        )

        execution_outcomes = _execute_workflow(workflow)
        cycle.execution_outcomes_json = _dump_json([item.model_dump(mode="json") for item in execution_outcomes])
        _record_stage(
            session=session,
            cycle=cycle,
            stage_history=stage_history,
            stage="work_executed",
            detail=f"Recorded {len(execution_outcomes)} completed execution outcomes.",
        )

        next_cycle_seed = [task.title for task in workflow.items]
        archive = OrchestrationArchive(
            cleaned_output=cleaned_output,
            daily_workflow=workflow,
            execution_outcomes=execution_outcomes,
            next_cycle_seed=next_cycle_seed,
        )
        cycle.archive_json = _dump_model(archive)
        cycle.next_cycle_seed_json = _dump_json(next_cycle_seed)
        _record_stage(
            session=session,
            cycle=cycle,
            stage_history=stage_history,
            stage="outcomes_archived",
            detail="Archived the cleaned workflow, outcomes, and replay seed together.",
        )

        cycle.status = "completed"
        _record_stage(
            session=session,
            cycle=cycle,
            stage_history=stage_history,
            stage="next_cycle_prepared",
            detail="Prepared the next cycle to start from the cleaned archive seed.",
        )
        return _build_cycle_response(
            cycle=cycle,
            agent_passes=agent_passes,
            cleaned_output=cleaned_output,
            daily_workflow=workflow,
            execution_outcomes=execution_outcomes,
            archive=archive,
            next_cycle_seed=next_cycle_seed,
            stage_history=stage_history,
            retry_policy=retry_policy,
        )
    except Exception as exc:
        cycle.status = "failed"
        cycle.failure_reason = str(exc)
        _record_stage(
            session=session,
            cycle=cycle,
            stage_history=stage_history,
            stage="failed",
            detail=str(exc),
            status="failed",
        )
        raise


def get_orchestration_cycle(*, session: Session, cycle_id: int) -> OrchestrationCycleResponse:
    cycle = session.get(OrchestrationCycle, cycle_id)
    if cycle is None:
        raise LookupError("orchestration cycle not found")

    agent_rows = list(
        session.exec(
            select(OrchestrationAgentPass)
            .where(OrchestrationAgentPass.cycle_id == cycle_id)
            .order_by(col(OrchestrationAgentPass.id))
        ).all()
    )
    agent_passes = [
        OrchestrationAgentPassRead.model_validate(json.loads(row.response_json))
        for row in agent_rows
    ]
    cleaned_output = _load_model(cycle.cleaned_output_json, OrchestrationCleanedOutput())
    workflow = _load_model(cycle.daily_workflow_json, OrchestrationWorkflow())
    execution_outcomes = [
        OrchestrationExecutionOutcome.model_validate(item)
        for item in _load_json(cycle.execution_outcomes_json, [])
    ]
    archive = _load_model(
        cycle.archive_json,
        OrchestrationArchive(
            cleaned_output=cleaned_output,
            daily_workflow=workflow,
            execution_outcomes=execution_outcomes,
            next_cycle_seed=_load_str_list(cycle.next_cycle_seed_json),
        ),
    )
    stage_history = [
        OrchestrationStageTransition.model_validate(item)
        for item in _load_json(cycle.stage_history_json, [])
    ]
    retry_policy = _load_model(cycle.retry_policy_json, OrchestrationRetryPolicy())
    return _build_cycle_response(
        cycle=cycle,
        agent_passes=agent_passes,
        cleaned_output=cleaned_output,
        daily_workflow=workflow,
        execution_outcomes=execution_outcomes,
        archive=archive,
        next_cycle_seed=_load_str_list(cycle.next_cycle_seed_json),
        stage_history=stage_history,
        retry_policy=retry_policy,
    )


def _build_agent_pass(
    *, command: str, archive_seed: Sequence[str], agent: OrchestrationAgentRequest
) -> OrchestrationAgentPassRead:
    name = _normalize_text(agent.name)
    role = _normalize_text(agent.role)
    if not name:
        raise ValueError("agent name is required")
    if not role:
        raise ValueError("agent role is required")

    findings = _stable_dedupe([command, *agent.focus, *archive_seed])[:3]
    actions = _stable_dedupe([*agent.focus, *archive_seed, command])[:3]
    return OrchestrationAgentPassRead(
        agent_name=name,
        role=role,
        findings=findings,
        actions=actions,
        summary=f"{name} completed one deterministic pass for role {role}.",
    )


def _clean_agent_outputs(
    *, agent_passes: Sequence[OrchestrationAgentPassRead], archive_seed: Sequence[str]
) -> OrchestrationCleanedOutput:
    findings = _stable_dedupe([item for agent_pass in agent_passes for item in agent_pass.findings])
    actions = _stable_dedupe([item for agent_pass in agent_passes for item in agent_pass.actions])
    return OrchestrationCleanedOutput(
        findings=findings,
        actions=actions,
        archive_seed=_stable_dedupe(archive_seed),
    )


def _build_daily_workflow(
    *, agent_passes: Sequence[OrchestrationAgentPassRead], cleaned_output: OrchestrationCleanedOutput
) -> OrchestrationWorkflow:
    items: list[OrchestrationWorkflowTask] = []
    for index, action in enumerate(cleaned_output.actions, start=1):
        source_agents = [
            agent_pass.agent_name
            for agent_pass in agent_passes
            if action in agent_pass.actions
        ]
        items.append(
            OrchestrationWorkflowTask(
                task_id=f"task-{index}",
                title=action,
                source_agents=_stable_dedupe(source_agents),
            )
        )
    return OrchestrationWorkflow(items=items)


def _execute_workflow(workflow: OrchestrationWorkflow) -> list[OrchestrationExecutionOutcome]:
    return [
        OrchestrationExecutionOutcome(
            task_id=item.task_id,
            result=f"Executed: {item.title}",
        )
        for item in workflow.items
    ]


def _record_stage(
    *,
    session: Session,
    cycle: OrchestrationCycle,
    stage_history: list[OrchestrationStageTransition],
    stage: StageName,
    detail: str,
    status: Literal["completed", "failed"] = "completed",
) -> None:
    transition = OrchestrationStageTransition(
        stage=stage,
        detail=detail,
        status=status,
        occurred_at=utcnow(),
    )
    stage_history.append(transition)
    cycle.current_stage = stage
    cycle.stage_history_json = _dump_json([item.model_dump(mode="json") for item in stage_history])
    cycle.updated_at = utcnow()
    session.add(cycle)
    session.commit()
    session.refresh(cycle)


def _build_cycle_response(
    *,
    cycle: OrchestrationCycle,
    agent_passes: list[OrchestrationAgentPassRead],
    cleaned_output: OrchestrationCleanedOutput,
    daily_workflow: OrchestrationWorkflow,
    execution_outcomes: list[OrchestrationExecutionOutcome],
    archive: OrchestrationArchive,
    next_cycle_seed: list[str],
    stage_history: list[OrchestrationStageTransition],
    retry_policy: OrchestrationRetryPolicy,
) -> OrchestrationCycleResponse:
    if cycle.id is None:
        raise ValueError("orchestration cycle id missing")
    return OrchestrationCycleResponse(
        cycle_id=cycle.id,
        status=cast(Literal["completed", "failed"], cycle.status),
        current_stage=cast(StageName, cycle.current_stage),
        command=cycle.command,
        seeded_from_cycle_id=cycle.seeded_from_cycle_id,
        agent_passes=agent_passes,
        cleaned_output=cleaned_output,
        daily_workflow=daily_workflow,
        execution_outcomes=execution_outcomes,
        archive=archive,
        next_cycle_seed=next_cycle_seed,
        stage_history=stage_history,
        retry_policy=retry_policy,
    )


def _load_prior_seed(*, session: Session, cycle_id: int | None) -> list[str]:
    if cycle_id is None:
        return []
    prior_cycle = session.get(OrchestrationCycle, cycle_id)
    if prior_cycle is None:
        raise LookupError("seed cycle not found")
    return _load_str_list(prior_cycle.next_cycle_seed_json)


ModelT = TypeVar("ModelT", bound=BaseModel)


def _load_model(raw: str | None, default: ModelT) -> ModelT:
    if not raw:
        return default
    return type(default).model_validate(json.loads(raw))


def _load_json(raw: str | None, default: list[object]) -> list[object]:
    if not raw:
        return default
    loaded = json.loads(raw)
    return loaded if isinstance(loaded, list) else default


def _load_str_list(raw: str | None) -> list[str]:
    return [str(item) for item in _load_json(raw, [])]


def _dump_model(model: object) -> str:
    return json.dumps(model.model_dump(mode="json"))  # type: ignore[reportAttributeAccessIssue]


def _dump_json(payload: object) -> str:
    return json.dumps(payload)


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def _stable_dedupe(items: Sequence[str] | Sequence[object]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = _normalize_text(str(item))
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped
