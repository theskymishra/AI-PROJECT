"""Environment physics and NOISY sensor emission.

This module owns the hidden ground truth. It is deliberately NOT Phase 5 work:
the environment samples observation symbols from the emission matrix, and the
HMM inverts that sampling in Phase 5. Building deterministic sensors first and
retrofitting noise later would produce an intermediate system that teaches the
reader to treat a sensor reading as ground truth, and would leave the HMM
posterior pinned near 1.0 -- the "looks hard-coded" failure the architecture
explicitly rules out.

The chain each tick:

    scenario sets targets
        -> rainfall and water level ramp toward them (deterministic)
        -> true_flood_state derived from water level thresholds (hidden)
        -> observation sampled from EMISSION_MATRIX[true_state]   (NOISY)
        -> raw gauge values jittered                              (NOISY)

Both noise sources draw from derive_rng(seed, tick, channel), so the whole
chain is reproducible despite being stochastic.
"""

from __future__ import annotations

from app.config import (
    EMISSION_MATRIX,
    FLOOD_REFERENCE_M,
    FLOOD_STATE_THRESHOLDS_M,
    RAINFALL_RAMP_MM_PER_TICK,
    RIVER_LEVEL_GAIN,
    RIVER_LEVEL_OFFSET_M,
    SENSOR_JITTER_RAINFALL_MM,
    SENSOR_JITTER_WATER_M,
    WATER_RAMP_M_PER_TICK,
)
from app.models.common import FloodState, Observation
from app.models.sensor import SensorReading
from app.simulation.rng import derive_rng, weighted_choice
from app.simulation.state import WorldState
from app.simulation.world import SENSOR_SPECS


def _ramp(current: float, target: float, rate: float) -> float:
    """Move current toward target by at most rate. Deterministic."""
    if current < target:
        return min(target, current + rate)
    if current > target:
        return max(target, current - rate)
    return current


def derive_true_flood_state(water_level_m: float) -> FloodState:
    """The hidden state. The agent never reads this."""
    if water_level_m >= FLOOD_STATE_THRESHOLDS_M["CRITICAL"]:
        return FloodState.CRITICAL
    if water_level_m >= FLOOD_STATE_THRESHOLDS_M["HIGH"]:
        return FloodState.HIGH
    if water_level_m >= FLOOD_STATE_THRESHOLDS_M["RISING"]:
        return FloodState.RISING
    return FloodState.NORMAL


def zone_flood_level(water_level_m: float, elevation: float) -> float:
    """How submerged a zone is, in [0, 1].

    Elevation is protective: Highland at 0.88 barely floods even at a water
    level that puts Riverside at 0.12 nearly under.
    """
    raw = (water_level_m / FLOOD_REFERENCE_M) * (1.0 - elevation)
    return max(0.0, min(1.0, raw))


def advance_environment(state: WorldState, seed: int) -> None:
    """Advance physics one tick and refresh every sensor.

    Called after the clock has already incremented, so state.clock.tick is the
    tick being computed.
    """
    tick = state.clock.tick
    env = state.environment

    env.rainfall_mm = _ramp(
        env.rainfall_mm, env.rainfall_target_mm, RAINFALL_RAMP_MM_PER_TICK
    )
    env.water_level_m = _ramp(
        env.water_level_m, env.water_target_m, WATER_RAMP_M_PER_TICK
    )
    env.river_level_m = env.water_level_m * RIVER_LEVEL_GAIN + RIVER_LEVEL_OFFSET_M
    env.true_flood_state = derive_true_flood_state(env.water_level_m).value

    _refresh_zone_flooding(state)
    _refresh_road_flooding(state)
    _emit_sensor_readings(state, seed, tick)


def _refresh_zone_flooding(state: WorldState) -> None:
    for zone in state.zones.values():
        zone.flood_level = round(
            zone_flood_level(state.environment.water_level_m, zone.elevation), 4
        )


def _refresh_road_flooding(state: WorldState) -> None:
    """A road is as impassable as its worst end."""
    node_by_id = state.world.node_by_id
    for road in state.roads.values():
        a_zone = state.zones[node_by_id[road.source].zone_id]
        b_zone = state.zones[node_by_id[road.destination].zone_id]
        road.flood_level = round(max(a_zone.flood_level, b_zone.flood_level), 4)


def _emit_sensor_readings(state: WorldState, seed: int, tick: int) -> None:
    """Produce one reading per sensor, with independent noise per sensor."""
    env = state.environment
    true_state = env.true_flood_state

    for sensor_id, zone_id, is_river_gauge in SENSOR_SPECS:
        zone = state.zones[zone_id]

        water_rng = derive_rng(seed, tick, f"sensor.water.{sensor_id}")
        rain_rng = derive_rng(seed, tick, f"sensor.rain.{sensor_id}")
        emit_rng = derive_rng(seed, tick, f"sensor.emission.{sensor_id}")

        # Local water depends on regional level and local elevation. River
        # gauges read the channel itself, which is deeper than the streets.
        base_water = (
            env.river_level_m
            if is_river_gauge
            else env.water_level_m * (1.0 - zone.elevation * 0.6)
        )
        water = max(0.0, base_water + water_rng.gauss(0.0, SENSOR_JITTER_WATER_M))
        rainfall = max(
            0.0, env.rainfall_mm + rain_rng.gauss(0.0, SENSOR_JITTER_RAINFALL_MM)
        )

        # THE IMPORTANT LINE. The symbol is sampled from the emission
        # distribution for the true state -- it is not read off water level.
        # Rows of EMISSION_MATRIX overlap, so a HIGH state regularly reports
        # MEDIUM_WATER. That overlap is what gives Phase 5's filter work to do.
        symbol = weighted_choice(emit_rng, EMISSION_MATRIX[true_state])

        state.add_sensor_reading(
            SensorReading(
                tick=tick,
                sensor_id=sensor_id,
                zone_id=zone_id,
                rainfall_mm=round(rainfall, 2),
                water_level_m=round(water, 3),
                river_level_m=round(env.river_level_m, 3),
                observation=Observation(symbol),
            )
        )
