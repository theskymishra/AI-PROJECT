"""Mutable per-run simulation state.

WorldState is the single source of truth for everything that changes. The
static geometry in world.py never mutates; this holds the copies that do.

ENVIRONMENT_VERSION
-------------------
``environment_version`` is the third component of the Phase 4 route cache key
``(start, goal, environment_version)``. A cached route whose key does not match
the current version can never be read, so stale routes are unreachable by
construction rather than by remembering to evict.

The version increments when a road's traversability meaningfully changes:

    blocked flag flips                       -> always
    flood_level moves by >= RISK_EPSILON     -> yes
    damage_level moves by >= RISK_EPSILON    -> yes
    failure_probability moves by >= EPSILON  -> yes (Phase 5 onward)
    sensor readings, clock ticks, emergencies, hospital capacity -> never

PHASE 0 CORRECTION. Section 2.1 of the architecture applied the epsilon to
failure_probability only, and listed a bare "flood_level or damage_level
changes" as an unconditional trigger. Flood level moves every tick while water
is rising, so that rule would bump the version on every tick and the route
cache would never serve a single hit -- the exact failure the epsilon exists to
prevent, reintroduced one row below it. The epsilon governs all three
continuous fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import (
    MAX_ALERTS,
    MAX_SENSOR_HISTORY,
    MAX_TIMELINE_ENTRIES,
    RISK_EPSILON,
)
from app.models.ambulance import Ambulance
from app.models.disaster import Zone
from app.models.emergency import Emergency
from app.models.events import Alert, TimelineEntry
from app.models.hospital import Hospital
from app.models.road import Road
from app.models.sensor import SensorReading
from app.models.shelter import Shelter
from app.simulation.clock import SimulationClock
from app.simulation.world import World, build_world


@dataclass
class Environment:
    """Physical conditions and the hidden ground truth.

    ``true_flood_state`` is what the world IS. Phase 5's HMM estimates it from
    noisy observations and will frequently disagree, which is the point.
    """

    rainfall_mm: float
    water_level_m: float
    river_level_m: float
    rainfall_target_mm: float
    water_target_m: float
    true_flood_state: str


@dataclass
class WorldState:
    """Everything that changes during a run."""

    world: World
    clock: SimulationClock
    scenario: str
    environment: Environment

    zones: dict[str, Zone]
    roads: dict[str, Road]
    hospitals: dict[str, Hospital]
    shelters: dict[str, Shelter]
    ambulances: dict[str, Ambulance]
    emergencies: dict[str, Emergency] = field(default_factory=dict)

    sensors: dict[str, SensorReading] = field(default_factory=dict)
    sensor_history: list[SensorReading] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)

    environment_version: int = 0
    seq: int = 0

    #: Snapshot of each road's traversability at the last version bump.
    _risk_baseline: dict[str, tuple[float, float, float]] = field(
        default_factory=dict, repr=False
    )
    _blocked_baseline: dict[str, bool] = field(default_factory=dict, repr=False)

    # -- construction ------------------------------------------------------

    @classmethod
    def create(cls, scenario: str, world: World | None = None) -> "WorldState":
        from app.config import (
            BASELINE_RAINFALL_MM,
            BASELINE_WATER_LEVEL_M,
            RIVER_LEVEL_GAIN,
            RIVER_LEVEL_OFFSET_M,
        )

        w = world or build_world()
        state = cls(
            world=w,
            clock=SimulationClock(),
            scenario=scenario,
            environment=Environment(
                rainfall_mm=BASELINE_RAINFALL_MM,
                water_level_m=BASELINE_WATER_LEVEL_M,
                river_level_m=BASELINE_WATER_LEVEL_M * RIVER_LEVEL_GAIN
                + RIVER_LEVEL_OFFSET_M,
                rainfall_target_mm=BASELINE_RAINFALL_MM,
                water_target_m=BASELINE_WATER_LEVEL_M,
                true_flood_state="NORMAL",
            ),
            # Deep copies: the static world must survive a reset untouched.
            zones={z.id: z.model_copy(deep=True) for z in w.zones},
            roads={r.id: r.model_copy(deep=True) for r in w.roads},
            hospitals={h.id: h.model_copy(deep=True) for h in w.hospitals},
            shelters={s.id: s.model_copy(deep=True) for s in w.shelters},
            ambulances={a.id: a.model_copy(deep=True) for a in w.ambulances},
        )
        state._capture_risk_baseline()
        return state

    # -- environment_version ----------------------------------------------

    def _capture_risk_baseline(self) -> None:
        self._risk_baseline = {
            r.id: (r.flood_level, r.damage_level, r.failure_probability)
            for r in self.roads.values()
        }
        self._blocked_baseline = {r.id: r.blocked for r in self.roads.values()}

    def reconcile_environment_version(self) -> list[str]:
        """Bump the version if any road's traversability changed materially.

        Returns the ids of the roads that triggered it, so the caller can emit
        a targeted road_status event rather than resending all 38.
        """
        changed: list[str] = []
        for road in self.roads.values():
            if self._blocked_baseline.get(road.id) != road.blocked:
                changed.append(road.id)
                continue
            before = self._risk_baseline.get(road.id)
            if before is None:
                changed.append(road.id)
                continue
            now = (road.flood_level, road.damage_level, road.failure_probability)
            if any(abs(n - b) >= RISK_EPSILON for n, b in zip(now, before)):
                changed.append(road.id)

        if changed:
            self.environment_version += 1
            self._capture_risk_baseline()
        return changed

    # -- bounded history ---------------------------------------------------

    def add_timeline(self, entry: TimelineEntry) -> None:
        self.timeline.append(entry)
        if len(self.timeline) > MAX_TIMELINE_ENTRIES:
            del self.timeline[: len(self.timeline) - MAX_TIMELINE_ENTRIES]

    def add_alert(self, alert: Alert) -> None:
        self.alerts.append(alert)
        if len(self.alerts) > MAX_ALERTS:
            del self.alerts[: len(self.alerts) - MAX_ALERTS]

    def add_sensor_reading(self, reading: SensorReading) -> None:
        self.sensors[reading.sensor_id] = reading
        self.sensor_history.append(reading)
        if len(self.sensor_history) > MAX_SENSOR_HISTORY:
            del self.sensor_history[: len(self.sensor_history) - MAX_SENSOR_HISTORY]

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq

    # -- derived figures ---------------------------------------------------

    @property
    def active_emergencies(self) -> list[Emergency]:
        return [
            e
            for e in self.emergencies.values()
            if e.status not in ("RESOLVED", "UNRESOLVABLE")
        ]

    def stats(self) -> dict[str, int]:
        """Figures the dashboard shows. Every one is counted, never invented."""
        active = self.active_emergencies
        roads = list(self.roads.values())
        return {
            "active_emergencies": len(active),
            "people_at_risk": sum(e.people_affected for e in active),
            "patients_awaiting_transport": sum(
                e.patients for e in active if e.status == "REPORTED"
            ),
            "available_ambulances": sum(
                1 for a in self.ambulances.values() if a.status == "AVAILABLE"
            ),
            "total_ambulances": len(self.ambulances),
            "available_beds": sum(h.available_beds for h in self.hospitals.values()),
            "total_beds": sum(h.total_beds for h in self.hospitals.values()),
            "available_icu": sum(h.available_icu for h in self.hospitals.values()),
            "blocked_roads": sum(1 for r in roads if r.blocked),
            "risky_roads": sum(1 for r in roads if r.status == "RISKY"),
            "total_roads": len(roads),
        }
