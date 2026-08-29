"""Simulation control endpoints.

POST mutates and returns a fresh snapshot. GET reads. State changes also reach
connected clients over SSE; the returned snapshot is a convenience so a caller
that just issued a command does not have to wait for the next frame.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import ALLOWED_SPEEDS
from app.simulation.engine import engine
from app.simulation.scenarios import SCENARIOS

router = APIRouter(prefix="/simulation", tags=["simulation"])


class SpeedRequest(BaseModel):
    speed: int = Field(description=f"One of {ALLOWED_SPEEDS}.")


class AdvanceRequest(BaseModel):
    ticks: int = Field(default=1, ge=1, le=600)


class ScenarioRequest(BaseModel):
    name: str


class ScenarioSummary(BaseModel):
    name: str
    label: str
    description: str
    duration_ticks: int


@router.get("/state", summary="Full simulation snapshot")
def get_state() -> dict[str, Any]:
    return engine.snapshot()


@router.get("/scenarios", response_model=list[ScenarioSummary])
def list_scenarios() -> list[ScenarioSummary]:
    return [
        ScenarioSummary(
            name=s.name,
            label=s.label,
            description=s.description,
            duration_ticks=s.duration_ticks,
        )
        for s in SCENARIOS.values()
    ]


@router.post("/start")
def start() -> dict[str, Any]:
    engine.start()
    return engine.snapshot()


@router.post("/pause")
def pause() -> dict[str, Any]:
    engine.pause()
    return engine.snapshot()


@router.post("/resume")
def resume() -> dict[str, Any]:
    engine.resume()
    return engine.snapshot()


@router.post("/reset")
def reset() -> dict[str, Any]:
    engine.reset()
    return engine.snapshot()


@router.post("/advance", summary="Step N ticks synchronously")
def advance(request: AdvanceRequest) -> dict[str, Any]:
    """Deterministic stepping, independent of the clock.

    This is what makes every integration test synchronous: no sleeps, no
    timing assumptions, identical results every run.
    """
    engine.advance(request.ticks)
    return engine.snapshot()


@router.post("/speed")
def set_speed(request: SpeedRequest) -> dict[str, Any]:
    try:
        engine.set_speed(request.speed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return engine.snapshot()


@router.post("/scenario")
def set_scenario(request: ScenarioRequest) -> dict[str, Any]:
    try:
        engine.set_scenario(request.name)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"unknown scenario {request.name!r}; available: {sorted(SCENARIOS)}",
        ) from exc
    return engine.snapshot()


class StreamHealth(BaseModel):
    subscribers: int
    dropped_frames: int
    seq: int
    status: Literal["IDLE", "RUNNING", "PAUSED", "COMPLETED"]


@router.get("/stream-health", response_model=StreamHealth)
def stream_health() -> StreamHealth:
    """Diagnostics for the SSE fan-out. Useful when a demo looks frozen."""
    return StreamHealth(
        subscribers=engine.broadcaster.subscriber_count,
        dropped_frames=engine.broadcaster.dropped_frames,
        seq=engine.state.seq,
        status=engine.state.clock.status.value,  # type: ignore[arg-type]
    )
