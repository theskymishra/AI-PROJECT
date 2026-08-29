"""The simulation engine.

Owns the single WorldState for the process and drives it forward one tick at a
time. Each tick:

    1. advance the clock by exactly one tick
    2. apply every scenario event scheduled for that tick
    3. advance environment physics and emit noisy sensor readings
    4. reconcile environment_version against RISK_EPSILON
    5. publish what changed over SSE

SINGLE PROCESS ONLY. All of this lives in memory. Running uvicorn with more
than one worker produces several divergent simulations with clients randomly
attached to each; app.main warns if it detects that.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.config import ALLOWED_SPEEDS, TICK_POLL_SECONDS, settings
from app.models.common import SimStatus
from app.models.events import SimEvent
from app.services.broadcast import Broadcaster
from app.simulation import sensors
from app.simulation.events import EventError, apply_event
from app.simulation.scenarios import DEFAULT_SCENARIO, SCENARIOS, get_scenario
from app.simulation.state import WorldState
from app.simulation.world import World, build_world

logger = logging.getLogger("aiders.engine")


class SimulationEngine:
    """Holds the world, the clock and the subscriber fan-out."""

    def __init__(self, world: World | None = None, seed: int | None = None) -> None:
        self._world: World = world or build_world()
        # The seed is INJECTED, not read from global settings at use time.
        # Settings is a frozen dataclass, so a test cannot monkeypatch it; more
        # importantly, an engine that reaches for a global cannot be
        # instantiated twice with different seeds in one process, which is
        # exactly what the reproducibility tests need to do.
        self.seed: int = settings.seed if seed is None else seed
        self.broadcaster = Broadcaster()
        self.state: WorldState = WorldState.create(DEFAULT_SCENARIO, self._world)

    # -- control -----------------------------------------------------------

    def start(self) -> None:
        clock = self.state.clock
        if clock.status is SimStatus.COMPLETED:
            self.reset(self.state.scenario)
            clock = self.state.clock
        clock.start(time.monotonic())
        self._publish_control("started")

    def pause(self) -> None:
        self.state.clock.pause()
        self._publish_control("paused")

    def resume(self) -> None:
        self.state.clock.resume(time.monotonic())
        self._publish_control("resumed")

    def reset(self, scenario: str | None = None) -> None:
        name = scenario or self.state.scenario
        get_scenario(name)  # raises KeyError before we destroy anything
        self.state = WorldState.create(name, self._world)
        self._publish_control("reset")

    def set_speed(self, speed: int) -> None:
        if speed not in ALLOWED_SPEEDS:
            raise ValueError(f"speed must be one of {ALLOWED_SPEEDS}, got {speed}")
        self.state.clock.set_speed(speed)
        self._publish_control("speed")

    def set_scenario(self, name: str) -> None:
        get_scenario(name)
        self.reset(name)

    # -- advancement -------------------------------------------------------

    def step(self) -> None:
        """Advance exactly one tick. The only place the world moves forward."""
        state = self.state
        scenario = get_scenario(state.scenario)

        tick = state.clock.advance_one()

        emergencies_changed: list[str] = []
        for event in scenario.events_at(tick):
            try:
                outcome = apply_event(state, event)
            except EventError:
                # A scripted event that no longer applies (a road already
                # blocked by the operator, say) is skipped, not fatal. The
                # simulation must never crash on normal interaction.
                logger.warning(
                    "scenario event skipped at tick %d: %s %s",
                    tick, event.type, event.payload,
                )
                continue
            if outcome.emergency_id:
                emergencies_changed.append(outcome.emergency_id)

        sensors.advance_environment(state, self.seed)

        roads_changed = state.reconcile_environment_version()

        if tick >= scenario.duration_ticks:
            state.clock.complete()

        self._publish_tick(roads_changed, emergencies_changed)

    def advance(self, ticks: int) -> int:
        """Step synchronously. The testing and manual-stepping entry point.

        Works regardless of clock status, which is what makes every
        integration test synchronous and free of sleeps.
        """
        if ticks < 1:
            raise ValueError("ticks must be >= 1")
        for _ in range(ticks):
            self.step()
        return self.state.clock.tick

    def pump(self) -> int:
        """Consume ticks due since the last pump. Driven by the background loop."""
        due = self.state.clock.pump(time.monotonic())
        for _ in range(due):
            self.step()
            if self.state.clock.status is not SimStatus.RUNNING:
                break
        return due

    # -- manual events -----------------------------------------------------

    def trigger(self, event_type: str, **payload: Any) -> dict[str, Any]:
        """Apply an operator-triggered event through the same path as scripts."""
        outcome = apply_event(
            self.state, SimEvent(tick=self.state.clock.tick, type=event_type, payload=payload)  # type: ignore[arg-type]
        )
        roads_changed = self.state.reconcile_environment_version()
        self._publish_tick(roads_changed, [outcome.emergency_id] if outcome.emergency_id else [])
        return {
            "headline": outcome.headline,
            "detail": outcome.detail,
            "environment_version": self.state.environment_version,
        }

    # -- serialisation -----------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Full state. Sent on connect and on any SSE sequence gap."""
        state = self.state
        scenario = get_scenario(state.scenario)
        return {
            "clock": self._clock_payload(),
            "scenario": {
                "name": scenario.name,
                "label": scenario.label,
                "description": scenario.description,
                "duration_ticks": scenario.duration_ticks,
            },
            "available_scenarios": [
                {"name": s.name, "label": s.label, "description": s.description}
                for s in SCENARIOS.values()
            ],
            "environment": self._environment_payload(),
            "stats": state.stats(),
            "nodes": [n.model_dump() for n in state.world.nodes],
            "zones": [z.model_dump() for z in state.zones.values()],
            "roads": [r.model_dump() for r in state.roads.values()],
            "emergencies": [e.model_dump() for e in state.emergencies.values()],
            "ambulances": [a.model_dump() for a in state.ambulances.values()],
            "hospitals": [h.model_dump() for h in state.hospitals.values()],
            "shelters": [s.model_dump() for s in state.shelters.values()],
            "sensors": [s.model_dump() for s in state.sensors.values()],
            "sensor_history": [s.model_dump() for s in state.sensor_history],
            "timeline": [t.model_dump() for t in state.timeline],
            "alerts": [a.model_dump() for a in state.alerts],
        }

    def _clock_payload(self) -> dict[str, Any]:
        clock = self.state.clock
        return {
            "tick": clock.tick,
            "speed": clock.speed,
            "status": clock.status.value,
            "elapsed_label": clock.elapsed_label,
        }

    def _environment_payload(self) -> dict[str, Any]:
        env = self.state.environment
        return {
            "rainfall_mm": round(env.rainfall_mm, 2),
            "water_level_m": round(env.water_level_m, 3),
            "river_level_m": round(env.river_level_m, 3),
            # Ground truth, labelled as such. Phase 5 adds the HMM's estimate
            # alongside it, and the gap between the two is the demonstration.
            "true_flood_state": env.true_flood_state,
            "environment_version": self.state.environment_version,
        }

    # -- publication -------------------------------------------------------

    def _publish_tick(
        self, roads_changed: list[str], emergencies_changed: list[str]
    ) -> None:
        state = self.state

        # WIRE CONTRACT
        # -------------
        # Fields below fall into two categories and the client treats them
        # differently. Getting this wrong is not a cosmetic bug: a client that
        # REPLACES its road list with a partial delta loses 37 of 38 roads the
        # first time one road changes.
        #
        #   COMPLETE  clock, environment, stats, sensors, hospitals
        #             -> always present, always the full set, replace wholesale
        #   PARTIAL   roads, emergencies
        #             -> present only when something changed, contains ONLY the
        #                changed entities, merge by id
        #   TAIL      timeline_tail, alerts_tail
        #             -> always present (empty list when nothing new), append
        #                by id with de-duplication
        #
        # timeline_tail and alerts_tail were previously omitted when empty.
        # An intermittently-absent field is a contract that clients get wrong,
        # and it crashed the dashboard reducer on the first quiet tick. They
        # are now always present.
        payload: dict[str, Any] = {
            "clock": self._clock_payload(),
            "environment": self._environment_payload(),
            "stats": state.stats(),
            "sensors": [s.model_dump() for s in state.sensors.values()],
            # Three hospitals. Cheaper to send every tick than to track which
            # events touch capacity, and it removes a staleness class outright.
            "hospitals": [h.model_dump() for h in state.hospitals.values()],
            "timeline_tail": [t.model_dump() for t in state.timeline[-5:]],
            "alerts_tail": [a.model_dump() for a in state.alerts[-5:]],
        }

        # Only resend roads that moved. 38 roads every tick would be wasteful
        # and would make the delta meaningless as a change signal.
        if roads_changed:
            payload["roads"] = [
                state.roads[rid].model_dump()
                for rid in roads_changed
                if rid in state.roads
            ]
        if emergencies_changed:
            payload["emergencies"] = [
                state.emergencies[eid].model_dump()
                for eid in emergencies_changed
                if eid in state.emergencies
            ]

        self.broadcaster.publish(
            seq=state.next_seq(), tick=state.clock.tick, type="tick", payload=payload
        )

    def _publish_control(self, action: str) -> None:
        self.broadcaster.publish(
            seq=self.state.next_seq(),
            tick=self.state.clock.tick,
            type="sim_control",
            payload={"action": action, "snapshot": self.snapshot()},
        )


#: Process-wide singleton. In-memory state, single worker.
engine = SimulationEngine()


async def run_engine_loop(target: SimulationEngine | None = None) -> None:
    """Background task: wake regularly and consume whatever ticks are due.

    Sleeping on a fixed poll and computing due ticks from elapsed real time --
    rather than sleeping for one tick's duration -- keeps the clock honest when
    the loop is late, and makes speed a pure multiplier on consumption rate.
    """
    eng = target or engine
    logger.info("simulation loop started (poll %.0f ms)", TICK_POLL_SECONDS * 1000)
    try:
        while True:
            await asyncio.sleep(TICK_POLL_SECONDS)
            try:
                eng.pump()
            except Exception:  # noqa: BLE001 - the loop must survive one bad tick
                logger.exception("error while stepping the simulation")
    except asyncio.CancelledError:
        logger.info("simulation loop stopped")
        raise
