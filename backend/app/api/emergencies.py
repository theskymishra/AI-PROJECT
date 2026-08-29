"""Emergency read and create endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.common import MAX_MEDICAL_PRIORITY, MIN_MEDICAL_PRIORITY, Severity
from app.simulation.engine import engine
from app.simulation.events import EventError

router = APIRouter(tags=["emergencies"])


class CreateEmergencyRequest(BaseModel):
    id: str | None = Field(
        default=None, description="Omit to auto-assign the next free id."
    )
    node_id: str
    severity: Severity
    people_affected: int = Field(ge=1)
    medical_priority: int = Field(
        ge=MIN_MEDICAL_PRIORITY, le=MAX_MEDICAL_PRIORITY
    )


@router.get("/emergencies")
def list_emergencies() -> list[dict[str, Any]]:
    return [e.model_dump() for e in engine.state.emergencies.values()]


@router.get("/emergencies/{emergency_id}")
def get_emergency(emergency_id: str) -> dict[str, Any]:
    emergency = engine.state.emergencies.get(emergency_id)
    if emergency is None:
        raise HTTPException(status_code=404, detail=f"no emergency {emergency_id}")
    return emergency.model_dump()


@router.post("/emergencies", status_code=201)
def create_emergency(request: CreateEmergencyRequest) -> dict[str, Any]:
    """Create an emergency. ``patients`` is derived, never supplied.

    patients = clamp(min(people_affected, 1 + medical_priority // 2), 1, 4)
    """
    emergency_id = request.id or _next_emergency_id()
    try:
        engine.trigger(
            "EMERGENCY_CREATED",
            id=emergency_id,
            node_id=request.node_id,
            severity=request.severity.value,
            people_affected=request.people_affected,
            medical_priority=request.medical_priority,
        )
    except EventError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return engine.state.emergencies[emergency_id].model_dump()


def _next_emergency_id() -> str:
    existing = engine.state.emergencies
    index = 1
    while f"E{index}" in existing:
        index += 1
    return f"E{index}"
