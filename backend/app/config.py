"""Central configuration for the AI-DERS backend.

Every tuning constant in the project lives here, so that a viva question of the
form "what happens if you change X?" has exactly one place to point at.

Phase 1 defines only the constants Phase 1 actually uses. Simulation, search,
CSP, probability and planning constants (SCALE_KM_PER_UNIT, the A* cost weights
alpha/beta/gamma, RISK_EPSILON, the HMM matrices, the noisy-OR parameters) are
added by the phase that introduces them, because a constant with no consumer is
dead code that misleads the reader about what the system currently does.

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
CURRENT_PHASE = 1
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
