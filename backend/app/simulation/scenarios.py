"""Deterministic scenario scripts.

Every event is scheduled on an integer TICK. Nothing here consults a clock, a
timestamp or a random number, so a scenario run at 5x produces a byte-identical
event log to the same scenario run at 1x. That property is asserted by
tests/integration/test_determinism.py.

Phase 2 ships four scenarios. MASS_EVACUATION, CRITICAL_FLOOD and
HOSPITAL_OVERLOAD arrive in Phase 10 with the rest of the real-time event work,
per the approved phase plan.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.events import SimEvent


@dataclass(frozen=True)
class Scenario:
    name: str
    label: str
    description: str
    #: Tick at which the run is marked COMPLETED.
    duration_ticks: int
    events: tuple[SimEvent, ...]

    def events_at(self, tick: int) -> tuple[SimEvent, ...]:
        return tuple(e for e in self.events if e.tick == tick)


def _e(tick: int, type_: str, **payload: object) -> SimEvent:
    return SimEvent(tick=tick, type=type_, payload=dict(payload))  # type: ignore[arg-type]


NORMAL = Scenario(
    name="NORMAL",
    label="Normal Conditions",
    description=(
        "Baseline. Light rain, low water, no incidents. Used to confirm the "
        "clock, the sensors and the event pipeline behave when nothing is wrong."
    ),
    duration_ticks=300,
    events=(),
)


MODERATE_FLOOD = Scenario(
    name="MODERATE_FLOOD",
    label="Moderate Flood",
    description=(
        "Water rises into the RISING band and stays there. Riverside floods "
        "partially; no road closures. One non-critical emergency."
    ),
    duration_ticks=420,
    events=(
        _e(30, "RAINFALL_CHANGE", target_mm=14.0),
        _e(60, "WATER_LEVEL_CHANGE", target_m=1.8),
        _e(150, "EMERGENCY_CREATED", id="E1", node_id="N2",
           severity="MEDIUM", people_affected=4, medical_priority=2),
        _e(240, "ROAD_DAMAGE", road_id="R17", damage_level=0.3),
        _e(330, "RAINFALL_CHANGE", target_mm=6.0),
        _e(360, "WATER_LEVEL_CHANGE", target_m=1.2),
    ),
)


# The demonstration scenario. Tick numbers follow the brief's timeline.
SEVERE_FLOOD = Scenario(
    name="SEVERE_FLOOD",
    label="Severe Flood",
    description=(
        "The headline scenario. Rainfall and water rise until the hidden flood "
        "state reaches CRITICAL, the Riverside Bridge (R17) closes, and "
        "emergencies appear in the flood plain. Corridor A is destroyed, "
        "forcing traffic onto the 52% longer northern route."
    ),
    duration_ticks=520,
    events=(
        _e(30,  "RAINFALL_CHANGE",     target_mm=22.0),
        _e(60,  "WATER_LEVEL_CHANGE",  target_m=2.2),
        _e(90,  "WATER_LEVEL_CHANGE",  target_m=3.1),
        _e(120, "RAINFALL_CHANGE",     target_mm=34.0),
        _e(140, "ROAD_DAMAGE",         road_id="R17", damage_level=0.65),
        # Corridor A dies here. Shortest route 44.8 km -> 68.3 km.
        _e(150, "ROAD_BLOCKED",        road_id="R17"),
        _e(180, "EMERGENCY_CREATED",   id="E7", node_id="N1",
            severity="CRITICAL", people_affected=9, medical_priority=5),
        _e(240, "WATER_LEVEL_CHANGE",  target_m=3.8),
        _e(270, "EMERGENCY_CREATED",   id="E8", node_id="N4",
            severity="HIGH", people_affected=5, medical_priority=4),
        # Corridor C's first hop. Riverside now reaches the network only
        # through Old Town.
        _e(300, "ROAD_BLOCKED",        road_id="R6"),
        _e(360, "HOSPITAL_OVERLOAD",   hospital_id="H2",
            available_beds=2, available_icu=0),
        _e(420, "RAINFALL_CHANGE",     target_mm=8.0),
        _e(450, "WATER_LEVEL_CHANGE",  target_m=2.4),
        _e(480, "ROAD_RESTORED",       road_id="R6"),
    ),
)


DYNAMIC_ROAD_FAILURE = Scenario(
    name="DYNAMIC_ROAD_FAILURE",
    label="Dynamic Road Failure",
    description=(
        "Roads close and reopen repeatedly at a moderate water level. Built to "
        "exercise route invalidation and replanning rather than flood physics: "
        "each corridor is taken out in turn."
    ),
    duration_ticks=480,
    events=(
        _e(30,  "WATER_LEVEL_CHANGE", target_m=2.0),
        _e(60,  "ROAD_BLOCKED",       road_id="R17"),   # corridor A
        _e(120, "EMERGENCY_CREATED",  id="E2", node_id="N1",
            severity="HIGH", people_affected=6, medical_priority=4),
        _e(180, "ROAD_BLOCKED",       road_id="R7"),    # corridor B first hop
        _e(240, "ROAD_RESTORED",      road_id="R17"),
        _e(300, "ROAD_BLOCKED",       road_id="R6"),    # corridor C first hop
        _e(360, "ROAD_RESTORED",      road_id="R7"),
        _e(420, "ROAD_RESTORED",      road_id="R6"),
    ),
)


SCENARIOS: dict[str, Scenario] = {
    s.name: s for s in (NORMAL, MODERATE_FLOOD, SEVERE_FLOOD, DYNAMIC_ROAD_FAILURE)
}

DEFAULT_SCENARIO = SEVERE_FLOOD.name


def get_scenario(name: str) -> Scenario:
    scenario = SCENARIOS.get(name)
    if scenario is None:
        raise KeyError(
            f"unknown scenario {name!r}; available: {sorted(SCENARIOS)}"
        )
    return scenario
