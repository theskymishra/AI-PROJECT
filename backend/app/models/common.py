"""Shared enums, identifier aliases and world-wide constants.

These are the vocabulary of the whole system. The TypeScript mirror lives at
frontend/src/types/index.ts and must be changed in the same commit as this file.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Identifier aliases
#
# Plain strings at runtime. They exist to make signatures readable and to make
# a future switch to a stricter id type a single-line change.
# --------------------------------------------------------------------------

NodeId = str
ZoneId = str
RoadId = str
EmergencyId = str
AmbulanceId = str
HospitalId = str
ShelterId = str
SensorId = str
AlertId = str

# --------------------------------------------------------------------------
# World constants
# --------------------------------------------------------------------------

#: Largest ambulance capacity in the fleet (A3 and A4 carry 4).
#: Emergency.patients is clamped to this so the CSP capacity constraint
#: ``ambulance.capacity >= emergency.patients`` can always be satisfied by at
#: least one ambulance. Raising fleet capacity means raising this constant.
MAX_AMBULANCE_CAPACITY = 4

#: Inclusive bounds on Emergency.medical_priority.
MIN_MEDICAL_PRIORITY = 1
MAX_MEDICAL_PRIORITY = 5


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EmergencyStatus(StrEnum):
    REPORTED = "REPORTED"
    ALLOCATED = "ALLOCATED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    TRANSPORTING = "TRANSPORTING"
    RESOLVED = "RESOLVED"
    UNRESOLVABLE = "UNRESOLVABLE"


class AmbulanceStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    AT_SCENE = "AT_SCENE"
    TRANSPORTING = "TRANSPORTING"
    BUSY = "BUSY"


class RoadStatus(StrEnum):
    """Derived from Road.blocked and Road.failure_probability, never stored raw."""

    SAFE = "SAFE"
    RISKY = "RISKY"
    BLOCKED = "BLOCKED"


class FloodState(StrEnum):
    """Hidden state space of the HMM, and the domain of the BN FloodSeverity node."""

    NORMAL = "NORMAL"
    RISING = "RISING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Observation(StrEnum):
    """HMM observation alphabet. Emitted with noise, never read off the true state."""

    LOW_WATER = "LOW_WATER"
    MEDIUM_WATER = "MEDIUM_WATER"
    HIGH_WATER = "HIGH_WATER"
    RAPIDLY_RISING = "RAPIDLY_RISING"


class SimStatus(StrEnum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class NodeKind(StrEnum):
    JUNCTION = "JUNCTION"
    FACILITY = "FACILITY"


class ElevationBand(StrEnum):
    """Static per-road terrain band. Parent of SurfaceWater in the Bayesian Network."""

    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class HospitalStatus(StrEnum):
    OPEN = "OPEN"
    STRAINED = "STRAINED"
    FULL = "FULL"


class ShelterStatus(StrEnum):
    OPEN = "OPEN"
    NEAR_FULL = "NEAR_FULL"
    FULL = "FULL"


class AlertLevel(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Position(BaseModel):
    """A point in map coordinate space (0..1000 x 0..700 units).

    Kilometres are obtained by multiplying by SCALE_KM_PER_UNIT, introduced in
    Phase 2 alongside the world builder.
    """

    x: float = Field(ge=0)
    y: float = Field(ge=0)
