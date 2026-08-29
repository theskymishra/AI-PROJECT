"""The reproducibility guarantee.

Everything else in the project rests on this: if the same scenario and seed do
not produce the same run, no demo can be rehearsed and no test can be trusted.
"""

import pytest

from app.simulation.engine import SimulationEngine
from app.simulation.scenarios import SCENARIOS


def _fingerprint(engine: SimulationEngine) -> dict:
    """Everything an observer could see, in a comparable form."""
    state = engine.state
    return {
        "tick": state.clock.tick,
        "environment_version": state.environment_version,
        "water": round(state.environment.water_level_m, 6),
        "rainfall": round(state.environment.rainfall_mm, 6),
        "true_flood_state": state.environment.true_flood_state,
        "roads": {
            r.id: (r.blocked, round(r.flood_level, 6), round(r.damage_level, 6))
            for r in state.roads.values()
        },
        "emergencies": {
            e.id: (e.severity.value, e.patients, e.people_affected, e.status.value)
            for e in state.emergencies.values()
        },
        "hospitals": {
            h.id: (h.available_beds, h.available_icu) for h in state.hospitals.values()
        },
        "observations": {
            s.sensor_id: s.observation.value for s in state.sensors.values()
        },
        "timeline": [(t.tick, t.category, t.headline) for t in state.timeline],
        "alerts": [(a.tick, a.level.value, a.title) for a in state.alerts],
    }


def _run(scenario: str, ticks: int, seed: int | None = None) -> dict:
    engine = SimulationEngine(seed=seed)
    engine.set_scenario(scenario)
    engine.advance(ticks)
    return _fingerprint(engine)


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_same_scenario_and_seed_produce_an_identical_run(scenario):
    assert _run(scenario, 200) == _run(scenario, 200)


def test_identical_result_regardless_of_playback_speed():
    """1x and 5x must produce the same world.

    Speed changes how fast ticks are consumed, never what a tick does. This is
    the property the integer tick clock exists to guarantee -- a wall-clock
    scheduler would fail here.
    """
    slow = SimulationEngine()
    slow.set_scenario("SEVERE_FLOOD")
    slow.set_speed(1)
    slow.advance(320)

    fast = SimulationEngine()
    fast.set_scenario("SEVERE_FLOOD")
    fast.set_speed(5)
    fast.advance(320)

    assert _fingerprint(slow) == _fingerprint(fast)


def test_pausing_partway_changes_nothing():
    straight = SimulationEngine()
    straight.set_scenario("SEVERE_FLOOD")
    straight.advance(300)

    interrupted = SimulationEngine()
    interrupted.set_scenario("SEVERE_FLOOD")
    interrupted.advance(120)
    interrupted.pause()
    interrupted.resume()
    interrupted.advance(180)

    assert _fingerprint(straight) == _fingerprint(interrupted)


def test_stepping_in_different_chunk_sizes_changes_nothing():
    one_go = SimulationEngine()
    one_go.set_scenario("SEVERE_FLOOD")
    one_go.advance(200)

    piecewise = SimulationEngine()
    piecewise.set_scenario("SEVERE_FLOOD")
    for _ in range(200):
        piecewise.advance(1)

    assert _fingerprint(one_go) == _fingerprint(piecewise)


def test_reset_returns_to_a_pristine_world():
    engine = SimulationEngine()
    engine.set_scenario("SEVERE_FLOOD")
    engine.advance(250)
    engine.reset()

    fresh = SimulationEngine()
    fresh.set_scenario("SEVERE_FLOOD")
    assert _fingerprint(engine) == _fingerprint(fresh)


def test_a_run_after_reset_reproduces_the_first_run():
    engine = SimulationEngine()
    engine.set_scenario("SEVERE_FLOOD")
    engine.advance(200)
    first = _fingerprint(engine)

    engine.reset()
    engine.advance(200)
    assert _fingerprint(engine) == first


def test_observations_are_noisy_yet_reproducible():
    """Both halves matter.

    Noisy, or the Phase 5 HMM has nothing to infer. Reproducible, or the demo
    cannot be rehearsed.
    """
    def observation_stream():
        engine = SimulationEngine()
        engine.set_scenario("SEVERE_FLOOD")
        out = []
        for _ in range(250):
            engine.advance(1)
            out.append(engine.state.sensors["SEN6"].observation.value)
        return out

    first = observation_stream()
    assert first == observation_stream()          # reproducible
    assert len(set(first)) >= 3                   # genuinely noisy


def test_a_different_seed_produces_a_different_run():
    """Different seed, same script: the scripted skeleton holds, the noise moves.

    Seeds are passed to the constructor rather than patched onto Settings,
    which is a frozen dataclass by design (see test_config.py). An engine that
    read a global seed could not be instantiated twice with different seeds in
    one process, so this test is also a check that the seed stays injectable.
    """
    baseline = _run("SEVERE_FLOOD", 200, seed=20260828)
    other = _run("SEVERE_FLOOD", 200, seed=999_999)

    # Scripted events are seed-independent: the bridge closes on tick 150
    # whatever the seed, because scenario events are scheduled on ticks.
    assert baseline["roads"]["R17"][0] == other["roads"]["R17"][0]

    # Sensor emission is seeded, so the observation symbols must differ
    # somewhere across six sensors and 200 ticks.
    assert baseline["observations"] != other["observations"], (
        "changing the seed changed nothing observable -- the sensor emission "
        "is not actually consuming the seed"
    )