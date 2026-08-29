"""Simulation events, alerts, timeline entries and the SSE envelope."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.common import AlertId, AlertLevel

#: Event types the scenario scripts and manual controls can emit.
EventType = Literal[
    "RAINFALL_CHANGE",
    "WATER_LEVEL_CHANGE",
    "ROAD_BLOCKED",
    "ROAD_RESTORED",
    "ROAD_DAMAGE",
    "EMERGENCY_CREATED",
    "HOSPITAL_OVERLOAD",
    "ROUTE_INVALIDATED",
    "REPLANNING",
    "ROUTE_UPDATED",
    "ALLOCATION_UPDATED",
    "PLAN_UPDATED",
    "EMERGENCY_RESOLVED",
]

#: Payload types pushed over Server-Sent Events. See Phase 0 section 9.
SSEEventType = Literal[
    "snapshot",
    "tick",
    "sensors",
    "belief",
    "kb_delta",
    "road_status",
    "emergency",
    "allocation",
    "route",
    "plan",
    "alert",
    "timeline",
    "sim_control",
]


class SimEvent(BaseModel):
    """A scheduled or manually triggered change to the environment.

    Scheduled on an integer TICK, never a wall-clock timestamp. This is what
    makes 1x, 2x and 5x playback produce identical event orderings.
    """

    tick: int = Field(ge=0)
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)


class TimelineEntry(BaseModel):
    id: str
    tick: int = Field(ge=0)
    category: str
    headline: str
    detail: str = ""
    ai_components: list[str] = Field(
        default_factory=list,
        description="Which AI subsystems produced this entry, e.g. ['HMM', 'A*'].",
    )


class Alert(BaseModel):
    id: AlertId
    tick: int = Field(ge=0)
    level: AlertLevel
    title: str
    message: str
    source: str


class SSEEnvelope(BaseModel):
    """Every Server-Sent Event is wrapped in this.

    ``seq`` is monotonically increasing per connection. A client that observes a
    gap refetches GET /api/simulation/state and re-snapshots, so a dropped
    connection self-heals instead of silently showing stale data.
    """

    seq: int = Field(ge=0)
    tick: int = Field(ge=0)
    type: SSEEventType
    payload: dict[str, Any] = Field(default_factory=dict)
