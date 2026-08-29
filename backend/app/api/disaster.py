"""Manual environment controls.

Operator-triggered events go through exactly the same apply_event path as
scripted ones, so a hand-blocked road behaves identically to a scripted one and
appears on the timeline without any extra bookkeeping.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.simulation.engine import engine
from app.simulation.events import EventError

router = APIRouter(prefix="/disaster", tags=["disaster"])


class RoadRequest(BaseModel):
    road_id: str


class RoadDamageRequest(BaseModel):
    road_id: str
    damage_level: float = Field(ge=0.0, le=1.0)


class EnvironmentUpdate(BaseModel):
    rainfall_delta_mm: float | None = None
    water_level_delta_m: float | None = None


class HospitalOverloadRequest(BaseModel):
    hospital_id: str
    available_beds: int = Field(default=0, ge=0)
    available_icu: int = Field(default=0, ge=0)


def _apply(event_type: str, **payload: Any) -> dict[str, Any]:
    try:
        return engine.trigger(event_type, **payload)
    except EventError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/road/block")
def block_road(request: RoadRequest) -> dict[str, Any]:
    return _apply("ROAD_BLOCKED", road_id=request.road_id)


@router.post("/road/restore")
def restore_road(request: RoadRequest) -> dict[str, Any]:
    return _apply("ROAD_RESTORED", road_id=request.road_id)


@router.post("/road/damage")
def damage_road(request: RoadDamageRequest) -> dict[str, Any]:
    return _apply(
        "ROAD_DAMAGE", road_id=request.road_id, damage_level=request.damage_level
    )


@router.post("/hospital/overload")
def overload_hospital(request: HospitalOverloadRequest) -> dict[str, Any]:
    return _apply(
        "HOSPITAL_OVERLOAD",
        hospital_id=request.hospital_id,
        available_beds=request.available_beds,
        available_icu=request.available_icu,
    )


@router.post("/update", summary="Nudge rainfall or water level")
def update_environment(request: EnvironmentUpdate) -> dict[str, Any]:
    if request.rainfall_delta_mm is None and request.water_level_delta_m is None:
        raise HTTPException(
            status_code=422,
            detail="supply rainfall_delta_mm, water_level_delta_m, or both",
        )

    results: list[dict[str, Any]] = []
    env = engine.state.environment

    if request.rainfall_delta_mm is not None:
        target = max(0.0, env.rainfall_target_mm + request.rainfall_delta_mm)
        results.append(_apply("RAINFALL_CHANGE", target_mm=target))
    if request.water_level_delta_m is not None:
        target = max(0.0, env.water_target_m + request.water_level_delta_m)
        results.append(_apply("WATER_LEVEL_CHANGE", target_m=target))

    return {"applied": results, "environment": engine._environment_payload()}
