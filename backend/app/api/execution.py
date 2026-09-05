"""Phase 10 HTN plan execution API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.execution import ExecutionResult
from app.services.execution_service import ExecutionError, execution_service
from app.simulation.engine import engine

router = APIRouter(tags=["ai-execution"])


def _safe(callable_):
    try:
        return callable_()
    except ExecutionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/ai/execution/prepare", response_model=ExecutionResult, summary="Prepare the current HTN plan for execution")
def prepare_execution() -> ExecutionResult:
    return execution_service.prepare(engine.state)


@router.post("/ai/execution/step", response_model=ExecutionResult, summary="Execute the next HTN action")
def execute_next() -> ExecutionResult:
    return _safe(lambda: execution_service.execute_next(engine))


@router.post("/ai/execution/all", response_model=ExecutionResult, summary="Execute all remaining HTN actions")
def execute_all() -> ExecutionResult:
    return _safe(lambda: execution_service.execute_all(engine))


@router.post("/ai/execution/reset", response_model=ExecutionResult, summary="Clear the execution cursor without resetting the simulation")
def reset_execution() -> ExecutionResult:
    return execution_service.reset_cursor(engine.state)
