"""Central configuration for the AI-DERS backend.

Every tuning constant in the project lives here, so that a viva question of the
form "what happens if you change X?" has exactly one place to point at.

Each constant is added by the phase that introduces it, because a constant with
no consumer is dead code that misleads the reader about what the system
currently does. Phase 1 added build identity and server settings; Phase 2 added
world geometry, the simulation clock, flood dynamics and the sensor emission
matrix. Still to come: the A* cost weights alpha/beta/gamma (Phase 4), the HMM
transition matrix and prior (Phase 5), and the Bayesian noisy-OR parameters
(Phase 5).

Settings are read from the environment once, at import time, via
``load_settings()``. Tests call ``load_settings()`` directly with a patched
environment rather than reloading this module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Build identity
# --------------------------------------------------------------------------

APP_NAME = "AI-DERS"
APP_FULL_NAME = "AI-Driven Disaster Evacuation & Emergency Response System"
APP_TAGLINE = "Intelligent emergency response under uncertainty."
VERSION = "0.1.0"
CURRENT_PHASE = 4
TOTAL_PHASES = 14
API_PREFIX = "/api"

# --------------------------------------------------------------------------
# Defaults (overridable by environment variables)
# --------------------------------------------------------------------------

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# The Vite dev server. Both spellings are allowed because browsers treat
# localhost and 127.0.0.1 as distinct origins for CORS purposes.
DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

# Master seed. Every random draw in the simulation is derived from this via
# derive_rng(seed, tick, channel) -- see Phase 0 section 3. Fixed seed plus
# tick-indexed derivation is what makes runs reproducible across speeds.
DEFAULT_SEED = 20260828


# --------------------------------------------------------------------------
# Phase 2: world geometry
# --------------------------------------------------------------------------

#: Map coordinate space is 1000 x 700 units. At this scale the region is
#: 50 km x 35 km. Every distance in the system is kilometres.
SCALE_KM_PER_UNIT = 0.05

MAP_WIDTH_UNITS = 1000
MAP_HEIGHT_UNITS = 700


# --------------------------------------------------------------------------
# Phase 2: simulation clock
# --------------------------------------------------------------------------

#: One tick is one simulated second.
SECONDS_PER_TICK = 1.0

#: How often the background loop wakes to consume due ticks.
TICK_POLL_SECONDS = 0.1

#: Speeds the UI may select. Speed changes how fast ticks are CONSUMED; it
#: never changes what happens on a given tick, which is why 1x and 5x produce
#: identical event logs.
ALLOWED_SPEEDS = (1, 2, 5)

#: Upper bound on ticks consumed in one pump. Without it, a laptop resuming
#: from sleep would try to catch up thousands of ticks in a single iteration
#: and block the event loop.
MAX_TICKS_PER_PUMP = 50


# --------------------------------------------------------------------------
# Phase 2: environment_version invalidation
# --------------------------------------------------------------------------

#: Minimum change in a road's continuous risk fields before the route cache is
#: invalidated.
#:
#: PHASE 0 CORRECTION. Phase 0 section 2.1 applied this epsilon to
#: failure_probability only, and listed bare "flood_level or damage_level
#: changes" as an unconditional trigger. Flood level moves every tick while
#: water is rising, so that rule would bump environment_version every tick and
#: the route cache would never serve a single hit. The epsilon applies to all
#: three continuous fields.
RISK_EPSILON = 0.05


# --------------------------------------------------------------------------
# Phase 2: flood dynamics (ENVIRONMENT ground truth, not inference)
# --------------------------------------------------------------------------

#: Water level in metres at or above which the true hidden flood state enters
#: each band. The environment owns this; the agent never sees it.
FLOOD_STATE_THRESHOLDS_M = {
    "RISING": 1.5,
    "HIGH": 2.5,
    "CRITICAL": 3.5,
}

#: How strongly a zone's elevation protects it from the regional water level.
#: zone_flood = clamp((water_level_m / FLOOD_REFERENCE_M) * (1 - elevation), 0, 1)
FLOOD_REFERENCE_M = 4.0

#: HMM emission matrix B. P(observation | true flood state).
#:
#: THIS LIVES IN PHASE 2 ON PURPOSE. The environment samples the observation
#: symbol from this distribution; the HMM inverts it in Phase 5. The rows
#: overlap deliberately -- a sensor in the HIGH state frequently reports
#: MEDIUM_WATER. Without that overlap the Phase 5 posterior would pin at ~1.0
#: every tick and the HMM panel would look hard-coded.
EMISSION_MATRIX = {
    "NORMAL":   {"LOW_WATER": 0.75, "MEDIUM_WATER": 0.20, "HIGH_WATER": 0.04, "RAPIDLY_RISING": 0.01},
    "RISING":   {"LOW_WATER": 0.20, "MEDIUM_WATER": 0.50, "HIGH_WATER": 0.20, "RAPIDLY_RISING": 0.10},
    "HIGH":     {"LOW_WATER": 0.05, "MEDIUM_WATER": 0.25, "HIGH_WATER": 0.50, "RAPIDLY_RISING": 0.20},
    "CRITICAL": {"LOW_WATER": 0.01, "MEDIUM_WATER": 0.09, "HIGH_WATER": 0.40, "RAPIDLY_RISING": 0.50},
}

#: Standard deviation of the measurement jitter added to raw gauge values, in
#: metres and millimetres respectively. Cosmetic relative to the emission
#: noise above, but it stops the sensor charts looking like staircases.
SENSOR_JITTER_WATER_M = 0.06
SENSOR_JITTER_RAINFALL_MM = 1.2

#: Bounded history retained in memory. This is a simulation, not a database.
# --------------------------------------------------------------------------
# Phase 4: A* routing
# --------------------------------------------------------------------------

#: Disaster-aware edge cost weights.
#:
#:     w(e) = distance(e) * (1 + ALPHA*flood + BETA*damage + GAMMA*P_fail)
#:
#: All three must stay >= 0: the admissibility proof in ai/search/road_graph.py
#: depends on the multiplier being >= 1. Raising them is always safe; a
#: negative value silently breaks A* optimality.
#:
#: A road with P_fail = 1 and no flooding costs 4x its length, which is enough
#: to push traffic onto a route up to four times longer to avoid it.
COST_WEIGHT_FLOOD = 2.0    # ALPHA
COST_WEIGHT_DAMAGE = 1.5   # BETA
COST_WEIGHT_FAILURE = 3.0  # GAMMA

#: PHASE NOTE: GAMMA multiplies road.failure_probability, which is 0.0 on
#: every road until the Bayesian Network lands in Phase 5. Until then routing
#: is flood- and damage-aware only. The term is wired and tested with injected
#: values so Phase 5 is a data change, not a code change.

MAX_TIMELINE_ENTRIES = 200
MAX_ALERTS = 50
MAX_SENSOR_HISTORY = 300

#: Ramp rates. Scenario events set a TARGET; the environment moves toward it at
#: this rate per tick. Ramping rather than stepping means the sensor charts show
#: a rising curve the HMM has to track, instead of an instant jump that would
#: make filtering trivial.
RAINFALL_RAMP_MM_PER_TICK = 0.35
WATER_RAMP_M_PER_TICK = 0.02

#: Baseline conditions at tick 0.
BASELINE_RAINFALL_MM = 2.0
BASELINE_WATER_LEVEL_M = 0.8

#: River level tracks the water gauge with a fixed offset and amplification.
RIVER_LEVEL_OFFSET_M = 1.4
RIVER_LEVEL_GAIN = 1.25


@dataclass(frozen=True)
class Settings:
    """Immutable resolved configuration."""

    app_name: str
    app_full_name: str
    app_tagline: str
    version: str
    phase: int
    total_phases: int
    api_prefix: str
    host: str
    port: int
    cors_origins: tuple[str, ...]
    seed: int


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(
            f"{name} must be an integer, got {raw!r}"
        ) from exc


def _env_origins(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    origins = tuple(part.strip() for part in raw.split(",") if part.strip())
    return origins or default


def load_settings() -> Settings:
    """Resolve settings from the current environment."""
    return Settings(
        app_name=APP_NAME,
        app_full_name=APP_FULL_NAME,
        app_tagline=APP_TAGLINE,
        version=VERSION,
        phase=CURRENT_PHASE,
        total_phases=TOTAL_PHASES,
        api_prefix=API_PREFIX,
        host=_env_str("AIDERS_HOST", DEFAULT_HOST),
        port=_env_int("AIDERS_PORT", DEFAULT_PORT),
        cors_origins=_env_origins("AIDERS_CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
        seed=_env_int("AIDERS_SEED", DEFAULT_SEED),
    )


settings = load_settings()
