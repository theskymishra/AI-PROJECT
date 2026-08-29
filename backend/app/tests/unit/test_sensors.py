"""Environment physics and noisy emission."""

import pytest

from app.config import EMISSION_MATRIX, FLOOD_STATE_THRESHOLDS_M, settings
from app.models.common import FloodState, Observation
from app.simulation.sensors import (
    advance_environment,
    derive_true_flood_state,
    zone_flood_level,
)
from app.simulation.state import WorldState


def _state():
    return WorldState.create("NORMAL")


# -- emission matrix -------------------------------------------------------


def test_every_emission_row_is_a_distribution():
    for state, row in EMISSION_MATRIX.items():
        assert sum(row.values()) == pytest.approx(1.0), state
        assert all(p >= 0 for p in row.values())


def test_emission_matrix_covers_every_state_and_symbol():
    assert set(EMISSION_MATRIX) == {s.value for s in FloodState}
    for row in EMISSION_MATRIX.values():
        assert set(row) == {o.value for o in Observation}


def test_emission_rows_overlap():
    """The property that gives Phase 5's HMM real work.

    If any state emitted one symbol deterministically, the posterior would pin
    at 1.0 whenever that symbol appeared and the panel would look hard-coded.
    """
    for state, row in EMISSION_MATRIX.items():
        assert max(row.values()) < 0.8, f"{state} is nearly deterministic"
        assert sum(1 for p in row.values() if p >= 0.05) >= 2


def test_no_symbol_uniquely_identifies_a_state():
    for symbol in (o.value for o in Observation):
        emitting = [s for s, row in EMISSION_MATRIX.items() if row[symbol] >= 0.05]
        assert len(emitting) >= 2, f"{symbol} would give the state away"


# -- hidden state ----------------------------------------------------------


@pytest.mark.parametrize(
    "water,expected",
    [
        (0.0, FloodState.NORMAL),
        (1.49, FloodState.NORMAL),
        (1.5, FloodState.RISING),
        (2.49, FloodState.RISING),
        (2.5, FloodState.HIGH),
        (3.49, FloodState.HIGH),
        (3.5, FloodState.CRITICAL),
        (9.0, FloodState.CRITICAL),
    ],
)
def test_true_flood_state_thresholds(water, expected):
    assert derive_true_flood_state(water) is expected


def test_thresholds_are_ordered():
    t = FLOOD_STATE_THRESHOLDS_M
    assert t["RISING"] < t["HIGH"] < t["CRITICAL"]


# -- zone flooding ---------------------------------------------------------


def test_elevation_protects_a_zone():
    low = zone_flood_level(3.0, elevation=0.12)
    high = zone_flood_level(3.0, elevation=0.88)
    assert low > high


def test_zone_flood_level_is_bounded():
    for water in (0.0, 2.0, 50.0):
        for elevation in (0.0, 0.5, 1.0):
            assert 0.0 <= zone_flood_level(water, elevation) <= 1.0


# -- emission in context ---------------------------------------------------


def test_every_sensor_reports_each_tick():
    state = _state()
    state.clock.advance_one()
    advance_environment(state, settings.seed)
    assert len(state.sensors) == 6


def test_observations_are_not_a_function_of_water_level():
    """The single most important test in this module.

    Hold the environment steady at CRITICAL and confirm the reported symbol
    varies. If it does not, the sensor is deterministic and Phase 5's HMM will
    have nothing to infer.
    """
    state = _state()
    state.environment.water_target_m = 4.0
    state.environment.water_level_m = 4.0
    seen = set()
    for _ in range(120):
        state.clock.advance_one()
        advance_environment(state, settings.seed)
        seen.add(state.sensors["SEN6"].observation)
    assert derive_true_flood_state(state.environment.water_level_m) is FloodState.CRITICAL
    assert len(seen) >= 2, f"emission is deterministic: only saw {seen}"


def test_noisy_emission_is_still_reproducible():
    def run():
        state = _state()
        state.environment.water_level_m = 2.8
        out = []
        for _ in range(40):
            state.clock.advance_one()
            advance_environment(state, settings.seed)
            out.append(state.sensors["SEN6"].observation.value)
        return out

    assert run() == run()


def test_emission_is_biased_toward_the_true_state():
    """Noisy, but not uninformative."""
    state = _state()
    state.environment.water_level_m = 4.0
    state.environment.water_target_m = 4.0   # else it ramps back to baseline
    counts: dict[str, int] = {}
    for _ in range(400):
        state.clock.advance_one()
        advance_environment(state, settings.seed)
        symbol = state.sensors["SEN6"].observation.value
        counts[symbol] = counts.get(symbol, 0) + 1
    wet = counts.get("HIGH_WATER", 0) + counts.get("RAPIDLY_RISING", 0)
    assert wet / 400 > 0.7


def test_water_and_rainfall_ramp_toward_their_targets():
    state = _state()
    state.environment.water_target_m = 3.0
    start = state.environment.water_level_m
    for _ in range(10):
        state.clock.advance_one()
        advance_environment(state, settings.seed)
    assert start < state.environment.water_level_m < 3.0


def test_ramp_stops_at_the_target():
    state = _state()
    state.environment.water_target_m = 1.0
    for _ in range(400):
        state.clock.advance_one()
        advance_environment(state, settings.seed)
    assert state.environment.water_level_m == pytest.approx(1.0)


def test_low_lying_roads_flood_before_highland_roads():
    state = _state()
    state.environment.water_target_m = 3.5
    state.environment.water_level_m = 3.5
    state.clock.advance_one()
    advance_environment(state, settings.seed)
    # R17 is the Riverside bridge; R32 is a Highland ridge road.
    assert state.roads["R17"].flood_level > state.roads["R32"].flood_level


def test_sensor_history_is_bounded():
    from app.config import MAX_SENSOR_HISTORY

    state = _state()
    for _ in range(120):
        state.clock.advance_one()
        advance_environment(state, settings.seed)
    assert len(state.sensor_history) <= MAX_SENSOR_HISTORY
