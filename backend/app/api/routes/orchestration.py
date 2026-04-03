from __future__ import annotations

# ruff: noqa: B008
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ...db import get_session
from ...schemas.orchestration import OrchestrationCycleCreate, OrchestrationCycleResponse
from ...services.orchestration_engine import (
    OrchestrationAgentRequest,
    OrchestrationEngineRequest,
    execute_orchestration_cycle,
    get_orchestration_cycle,
)

router = APIRouter(tags=["orchestration"])


@router.post("/orchestration/cycles", response_model=OrchestrationCycleResponse)
def run_orchestration_cycle(
    payload: OrchestrationCycleCreate,
    session: Session = Depends(get_session),
) -> OrchestrationCycleResponse:
    try:
        return execute_orchestration_cycle(
            session=session,
            req=OrchestrationEngineRequest(
                command=payload.command,
                agents=tuple(
                    OrchestrationAgentRequest(
                        name=agent.name,
                        role=agent.role,
                        focus=tuple(agent.focus),
                    )
                    for agent in payload.agents
                ),
                archive_seed=tuple(payload.archive_seed),
                seeded_from_cycle_id=payload.seed_cycle_id,
            ),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/orchestration/cycles/{cycle_id}", response_model=OrchestrationCycleResponse)
def read_orchestration_cycle(
    cycle_id: int,
    session: Session = Depends(get_session),
) -> OrchestrationCycleResponse:
    try:
        return get_orchestration_cycle(session=session, cycle_id=cycle_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
