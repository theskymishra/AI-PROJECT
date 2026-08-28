"""Pydantic data models for AI-DERS.

FROZEN CONTRACT (Phase 1). The TypeScript mirror is frontend/src/types/index.ts.
Any change to a shape here must be made in the same commit as the corresponding
change there, and agreed by all three team members (Phase 0 section 12).
"""

from app.models.ai_result import (
    BayesResult,
    CSPAssignment,
    CSPResult,
    CSPTraceStep,
    FOLResult,
    HMMResult,
    InferenceResult,
    InferenceStep,
    PlanAction,
    PlanNode,
    PlanResult,
    RouteResult,
)
from app.models.ambulance import Ambulance, EdgePosition
from app.models.common import (
    MAX_AMBULANCE_CAPACITY,
    MAX_MEDICAL_PRIORITY,
    MIN_MEDICAL_PRIORITY,
    AlertLevel,
    AmbulanceStatus,
    ElevationBand,
    EmergencyStatus,
    FloodState,
    HospitalStatus,
    NodeKind,
    Observation,
    Position,
    RoadStatus,
    Severity,
    ShelterStatus,
    SimStatus,
)
from app.models.disaster import Node, Zone
from app.models.emergency import Emergency, derive_patients
from app.models.events import Alert, SimEvent, SSEEnvelope, TimelineEntry
from app.models.hospital import Hospital
from app.models.road import Road
from app.models.sensor import SensorReading
from app.models.shelter import Shelter

__all__ = [
    "MAX_AMBULANCE_CAPACITY",
    "MAX_MEDICAL_PRIORITY",
    "MIN_MEDICAL_PRIORITY",
    "Alert",
    "AlertLevel",
    "Ambulance",
    "AmbulanceStatus",
    "BayesResult",
    "CSPAssignment",
    "CSPResult",
    "CSPTraceStep",
    "EdgePosition",
    "ElevationBand",
    "Emergency",
    "EmergencyStatus",
    "FOLResult",
    "FloodState",
    "HMMResult",
    "Hospital",
    "HospitalStatus",
    "InferenceResult",
    "InferenceStep",
    "Node",
    "NodeKind",
    "Observation",
    "PlanAction",
    "PlanNode",
    "PlanResult",
    "Position",
    "Road",
    "RoadStatus",
    "RouteResult",
    "SSEEnvelope",
    "SensorReading",
    "Severity",
    "Shelter",
    "ShelterStatus",
    "SimEvent",
    "SimStatus",
    "TimelineEntry",
    "Zone",
    "derive_patients",
]
