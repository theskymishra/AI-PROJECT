"""Event application.

Every change to the environment -- scheduled by a scenario or triggered by the
operator -- goes through apply_event. One code path means a manually blocked
road behaves identically to a scripted one, and the timeline is complete by
construction rather than because each call site remembered to log.

Events are scheduled on integer TICKS, never wall-clock times.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.common import AlertLevel, Severity
from app.models.emergency import Emergency
from app.models.events import Alert, SimEvent, TimelineEntry
from app.simulation.state import WorldState


class EventError(ValueError):
    """An event that cannot be applied to the current state."""


@dataclass(frozen=True)
class EventOutcome:
    """What an applied event changed, so the caller can broadcast precisely."""

    headline: str
    detail: str
    category: str
    alert_level: AlertLevel | None = None
    roads_changed: tuple[str, ...] = ()
    emergency_id: str | None = None


def _timeline_id(state: WorldState) -> str:
    return f"TL{len(state.timeline) + 1:04d}"


def apply_event(state: WorldState, event: SimEvent) -> EventOutcome:
    """Apply one event, record it on the timeline, and return what changed."""
    handler = _HANDLERS.get(event.type)
    if handler is None:
        raise EventError(f"unknown event type: {event.type}")

    outcome = handler(state, event.payload)

    state.add_timeline(
        TimelineEntry(
            id=_timeline_id(state),
            tick=state.clock.tick,
            category=outcome.category,
            headline=outcome.headline,
            detail=outcome.detail,
            # Phase 2 events are environmental. AI components appear on
            # timeline entries from Phase 4 onward.
            ai_components=[],
        )
    )

    if outcome.alert_level is not None:
        state.add_alert(
            Alert(
                id=f"AL{len(state.alerts) + 1:04d}",
                tick=state.clock.tick,
                level=outcome.alert_level,
                title=outcome.headline,
                message=outcome.detail,
                source="simulation",
            )
        )

    return outcome


# -- handlers --------------------------------------------------------------


def _rainfall_change(state: WorldState, payload: dict[str, Any]) -> EventOutcome:
    target = float(payload["target_mm"])
    if target < 0:
        raise EventError("target_mm must be >= 0")
    previous = state.environment.rainfall_target_mm
    state.environment.rainfall_target_mm = target
    direction = "increasing" if target > previous else "easing"
    return EventOutcome(
        category="WEATHER",
        headline=f"RAINFALL {direction.upper()}",
        detail=f"Target {previous:.1f} -> {target:.1f} mm/h.",
        alert_level=AlertLevel.WARNING if target >= 25 else None,
    )


def _water_level_change(state: WorldState, payload: dict[str, Any]) -> EventOutcome:
    target = float(payload["target_m"])
    if target < 0:
        raise EventError("target_m must be >= 0")
    previous = state.environment.water_target_m
    state.environment.water_target_m = target
    direction = "RISING" if target > previous else "RECEDING"
    return EventOutcome(
        category="WATER",
        headline=f"WATER LEVEL {direction}",
        detail=f"Target {previous:.2f} -> {target:.2f} m.",
        alert_level=AlertLevel.CRITICAL if target >= 3.5 else None,
    )


def _road_blocked(state: WorldState, payload: dict[str, Any]) -> EventOutcome:
    road_id = str(payload["road_id"])
    road = state.roads.get(road_id)
    if road is None:
        raise EventError(f"unknown road: {road_id}")
    if road.blocked:
        raise EventError(f"road {road_id} is already blocked")
    road.blocked = True
    return EventOutcome(
        category="ROAD",
        headline=f"ROAD {road_id} BLOCKED",
        detail=(
            f"{state.world.node_by_id[road.source].name} to "
            f"{state.world.node_by_id[road.destination].name} is impassable."
        ),
        alert_level=AlertLevel.CRITICAL,
        roads_changed=(road_id,),
    )


def _road_restored(state: WorldState, payload: dict[str, Any]) -> EventOutcome:
    road_id = str(payload["road_id"])
    road = state.roads.get(road_id)
    if road is None:
        raise EventError(f"unknown road: {road_id}")
    if not road.blocked:
        raise EventError(f"road {road_id} is not blocked")
    road.blocked = False
    return EventOutcome(
        category="ROAD",
        headline=f"ROAD {road_id} REOPENED",
        detail=(
            f"{state.world.node_by_id[road.source].name} to "
            f"{state.world.node_by_id[road.destination].name} is passable again."
        ),
        alert_level=AlertLevel.INFO,
        roads_changed=(road_id,),
    )


def _road_damage(state: WorldState, payload: dict[str, Any]) -> EventOutcome:
    road_id = str(payload["road_id"])
    level = float(payload["damage_level"])
    road = state.roads.get(road_id)
    if road is None:
        raise EventError(f"unknown road: {road_id}")
    if not 0.0 <= level <= 1.0:
        raise EventError("damage_level must be in [0, 1]")
    previous = road.damage_level
    road.damage_level = level
    return EventOutcome(
        category="ROAD",
        headline=f"ROAD {road_id} DAMAGE {level:.0%}",
        detail=f"Structural damage {previous:.0%} -> {level:.0%}.",
        alert_level=AlertLevel.WARNING if level >= 0.6 else None,
        roads_changed=(road_id,),
    )


def _emergency_created(state: WorldState, payload: dict[str, Any]) -> EventOutcome:
    emergency_id = str(payload["id"])
    if emergency_id in state.emergencies:
        raise EventError(f"emergency {emergency_id} already exists")

    node_id = str(payload["node_id"])
    node = state.world.node_by_id.get(node_id)
    if node is None:
        raise EventError(f"unknown node: {node_id}")

    emergency = Emergency.create(
        id=emergency_id,
        node_id=node_id,
        zone_id=node.zone_id,
        severity=Severity(payload["severity"]),
        people_affected=int(payload["people_affected"]),
        medical_priority=int(payload["medical_priority"]),
        reported_at_tick=state.clock.tick,
    )
    state.emergencies[emergency_id] = emergency

    return EventOutcome(
        category="EMERGENCY",
        headline=f"EMERGENCY {emergency_id} REPORTED",
        detail=(
            f"{emergency.severity.value} at {node.name}. "
            f"{emergency.people_affected} affected, "
            f"{emergency.patients} requiring transport."
        ),
        alert_level=(
            AlertLevel.CRITICAL
            if emergency.severity is Severity.CRITICAL
            else AlertLevel.WARNING
        ),
        emergency_id=emergency_id,
    )


def _hospital_overload(state: WorldState, payload: dict[str, Any]) -> EventOutcome:
    hospital_id = str(payload["hospital_id"])
    hospital = state.hospitals.get(hospital_id)
    if hospital is None:
        raise EventError(f"unknown hospital: {hospital_id}")

    beds = int(payload.get("available_beds", 0))
    icu = int(payload.get("available_icu", 0))
    if beds > hospital.total_beds or icu > hospital.total_icu:
        raise EventError("cannot set availability above capacity")

    previous = hospital.available_beds
    hospital.available_beds = max(0, beds)
    hospital.available_icu = max(0, icu)

    return EventOutcome(
        category="HOSPITAL",
        headline=f"HOSPITAL {hospital_id} {hospital.status.value}",
        detail=(
            f"{hospital.name}: beds {previous} -> {hospital.available_beds}, "
            f"ICU {hospital.available_icu} free."
        ),
        alert_level=(
            AlertLevel.CRITICAL
            if hospital.available_beds == 0
            else AlertLevel.WARNING
        ),
    )


_HANDLERS = {
    "RAINFALL_CHANGE": _rainfall_change,
    "WATER_LEVEL_CHANGE": _water_level_change,
    "ROAD_BLOCKED": _road_blocked,
    "ROAD_RESTORED": _road_restored,
    "ROAD_DAMAGE": _road_damage,
    "EMERGENCY_CREATED": _emergency_created,
    "HOSPITAL_OVERLOAD": _hospital_overload,
}
