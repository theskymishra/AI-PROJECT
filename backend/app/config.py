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
CURRENT_PHASE = 14
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
#: PHASE 5 ARCHITECTURE: the Bayesian Network's inferred P(failure) is the
#: ONLY risk input to A*. ALPHA and BETA are deliberately zero.
#:
#: WHY, because this looks like dead code otherwise:
#:
#:   1. road.flood_level and road.damage_level are ENVIRONMENT GROUND TRUTH.
#:      The whole architecture is "agent perceives noisy sensors, infers hidden
#:      state". Letting A* read those fields directly bypasses the inference
#:      chain -- the agent would be reading the answer instead of inferring it.
#:
#:   2. Both fields are already INPUTS to the Bayesian Network (via the
#:      SurfaceWater and RoadDamage nodes). Feeding them to the cost function
#:      as well double-counts the same evidence.
#:
#:   3. Measured in Phase 5: with ALPHA = 2.0 the two terms are collinear --
#:      both track terrain elevation -- so GAMMA scaled every route's cost
#:      proportionally and changed NO route across all 552 node pairs. The
#:      Bayesian Network had zero effect on routing. Setting ALPHA = 0 is what
#:      makes it load-bearing.
#:
#: The weights remain parameters of edge_cost() rather than constants, so the
#: unit tests can still exercise each term independently.
COST_WEIGHT_FLOOD = 0.0    # ALPHA -- retired, see above
COST_WEIGHT_DAMAGE = 0.0   # BETA  -- retired, see above
COST_WEIGHT_FAILURE = 3.0  # GAMMA -- the inferred risk term


# --------------------------------------------------------------------------
# Phase 6: symbolic knowledge engine
# --------------------------------------------------------------------------

#: Roads at or above this inferred failure probability become the symbolic
#: HighFailureProb(R) fact.  The value is deliberately the same 0.6 threshold
#: consumed by the Phase 7 CSP and documented in the Phase 5 hand-off.
KNOWLEDGE_HIGH_FAILURE_THRESHOLD = 0.60

# --------------------------------------------------------------------------
# Phase 5: Hidden Markov Model
# --------------------------------------------------------------------------

#: Hidden state space, in fixed order. Every vector in the HMM and the
#: FloodSeverity node of the Bayesian Network uses this ordering.
FLOOD_STATES = ("NORMAL", "RISING", "HIGH", "CRITICAL")

#: Observation alphabet, in fixed order.
OBSERVATIONS = ("LOW_WATER", "MEDIUM_WATER", "HIGH_WATER", "RAPIDLY_RISING")

#: Transition matrix A. A[from][to] = P(state_t = to | state_t-1 = from).
#:
#: Deliberately an APPROXIMATION of the environment's true dynamics, not a
#: copy of them. The simulator derives the true flood state from water-level
#: thresholds; this matrix is the AGENT's model of how flooding evolves. An
#: HMM whose transition model exactly matched the generator would be reading
#: the answer rather than inferring it. The mismatch is the point, and it is
#: worth saying so in a viva.
TRANSITION_MATRIX = {
    "NORMAL":   {"NORMAL": 0.85, "RISING": 0.13, "HIGH": 0.02, "CRITICAL": 0.00},
    "RISING":   {"NORMAL": 0.10, "RISING": 0.70, "HIGH": 0.18, "CRITICAL": 0.02},
    "HIGH":     {"NORMAL": 0.02, "RISING": 0.15, "HIGH": 0.68, "CRITICAL": 0.15},
    "CRITICAL": {"NORMAL": 0.00, "RISING": 0.03, "HIGH": 0.22, "CRITICAL": 0.75},
}

#: Prior belief at tick 0. The agent starts believing conditions are normal.
FLOOD_PRIOR = {"NORMAL": 0.90, "RISING": 0.08, "HIGH": 0.02, "CRITICAL": 0.00}

# EMISSION_MATRIX is defined in the Phase 2 block above. It lives there
# because the ENVIRONMENT samples observations from it; the HMM merely
# inverts it. One matrix, two users, no chance of them drifting apart.


# --------------------------------------------------------------------------
# Phase 5: Bayesian Network
# --------------------------------------------------------------------------

#: P(Rainfall). Overridden by hard evidence from the rain sensor in live mode.
RAINFALL_PRIOR = {"LOW": 0.60, "MED": 0.30, "HIGH": 0.10}

#: P(WaterLevel | Rainfall)
WATER_LEVEL_CPT = {
    "LOW":  {"LOW": 0.75, "MED": 0.20, "HIGH": 0.05},
    "MED":  {"LOW": 0.30, "MED": 0.50, "HIGH": 0.20},
    "HIGH": {"LOW": 0.08, "MED": 0.37, "HIGH": 0.55},
}

#: P(FloodSeverity | Rainfall, WaterLevel)
FLOOD_SEVERITY_CPT = {
    ("LOW", "LOW"):   {"NORMAL": 0.85, "RISING": 0.12, "HIGH": 0.03, "CRITICAL": 0.00},
    ("LOW", "MED"):   {"NORMAL": 0.45, "RISING": 0.40, "HIGH": 0.13, "CRITICAL": 0.02},
    ("LOW", "HIGH"):  {"NORMAL": 0.10, "RISING": 0.35, "HIGH": 0.40, "CRITICAL": 0.15},
    ("MED", "LOW"):   {"NORMAL": 0.60, "RISING": 0.30, "HIGH": 0.09, "CRITICAL": 0.01},
    ("MED", "MED"):   {"NORMAL": 0.25, "RISING": 0.45, "HIGH": 0.25, "CRITICAL": 0.05},
    ("MED", "HIGH"):  {"NORMAL": 0.05, "RISING": 0.25, "HIGH": 0.45, "CRITICAL": 0.25},
    ("HIGH", "LOW"):  {"NORMAL": 0.40, "RISING": 0.40, "HIGH": 0.17, "CRITICAL": 0.03},
    ("HIGH", "MED"):  {"NORMAL": 0.10, "RISING": 0.35, "HIGH": 0.40, "CRITICAL": 0.15},
    ("HIGH", "HIGH"): {"NORMAL": 0.02, "RISING": 0.10, "HIGH": 0.38, "CRITICAL": 0.50},
}

#: P(SurfaceWater | WaterLevel, ElevationBand)
#:
#: THE SECOND PATHWAY. This is what stops the live network collapsing into a
#: relabelling of the HMM belief: the current gauge reading reaches each road
#: directly, weighted by that road's terrain, without passing through
#: FloodSeverity at all. A low-lying Riverside road gets deep surface water the
#: moment water rises, while the HMM belief is still lagging in RISING.
SURFACE_WATER_CPT = {
    ("LOW", "HIGH"):  {"DRY": 0.95, "SHALLOW": 0.05, "DEEP": 0.00},
    ("LOW", "MED"):   {"DRY": 0.90, "SHALLOW": 0.09, "DEEP": 0.01},
    ("LOW", "LOW"):   {"DRY": 0.75, "SHALLOW": 0.20, "DEEP": 0.05},
    ("MED", "HIGH"):  {"DRY": 0.80, "SHALLOW": 0.18, "DEEP": 0.02},
    ("MED", "MED"):   {"DRY": 0.50, "SHALLOW": 0.38, "DEEP": 0.12},
    ("MED", "LOW"):   {"DRY": 0.20, "SHALLOW": 0.50, "DEEP": 0.30},
    ("HIGH", "HIGH"): {"DRY": 0.55, "SHALLOW": 0.35, "DEEP": 0.10},
    ("HIGH", "MED"):  {"DRY": 0.20, "SHALLOW": 0.45, "DEEP": 0.35},
    ("HIGH", "LOW"):  {"DRY": 0.03, "SHALLOW": 0.27, "DEEP": 0.70},
}

#: P(RoadFailure = TRUE | FloodSeverity, RoadDamage, SurfaceWater) via NOISY-OR.
#:
#:   P(fail) = 1 - (1-leak)*(1-f_S(s))*(1-f_D(d))*(1-f_W(w))
#:
#: 11 parameters instead of 36 hand-written CPT rows. Noisy-OR is a standard
#: canonical model (Russell & Norvig), it is monotone in every argument so its
#: behaviour is predictable, and it is explainable in one line at a viva.
NOISY_OR_LEAK = 0.01
NOISY_OR_FLOOD_SEVERITY = {"NORMAL": 0.01, "RISING": 0.15, "HIGH": 0.45, "CRITICAL": 0.75}
NOISY_OR_ROAD_DAMAGE = {"NONE": 0.01, "MINOR": 0.20, "MAJOR": 0.55}
NOISY_OR_SURFACE_WATER = {"DRY": 0.01, "SHALLOW": 0.30, "DEEP": 0.70}

#: Discretisation thresholds turning continuous sensor values into the
#: network's categorical evidence.
RAINFALL_BANDS_MM = {"LOW": 5.0, "MED": 20.0}    # >= 20 is HIGH
WATER_LEVEL_BANDS_M = {"LOW": 1.5, "MED": 2.8}   # >= 2.8 is HIGH
ROAD_DAMAGE_BANDS = {"NONE": 0.2, "MINOR": 0.6}  # >= 0.6 is MAJOR

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
