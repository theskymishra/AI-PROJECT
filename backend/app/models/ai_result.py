"""Result envelopes returned by the AI subsystems.

FROZEN CONTRACT. These shapes are what the frontend panels bind to and what the
integration tests assert against. They are declared in Phase 1 so that frontend
work is never blocked waiting for an algorithm, per the contract-first strategy
in Phase 0 section 12.

Every metric field here (nodes_expanded, backtracks, execution_ms, ...) must be
produced by the algorithm that owns it. None of them may be hard-coded.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.common import (
    AmbulanceId,
    EmergencyId,
    FloodState,
    HospitalId,
    NodeId,
    Observation,
    RoadId,
)


class RouteResult(BaseModel):
    """Output of A* over the road graph (Phase 4)."""

    found: bool
    path: list[NodeId] = Field(default_factory=list)
    edges: list[RoadId] = Field(default_factory=list)
    total_cost: float = Field(default=0.0, description="Risk-weighted kilometres.")
    total_distance: float = Field(default=0.0, description="Plain kilometres.")
    nodes_generated: int = 0
    nodes_expanded: int = 0
    execution_ms: float = 0.0
    expansion_order: list[NodeId] = Field(
        default_factory=list, description="Feeds the SearchVisualizer animation."
    )
    environment_version: int = Field(
        default=0, description="Route cache key component; see Phase 0 section 2.1."
    )
    failure_reason: str | None = None


class CSPAssignment(BaseModel):
    ambulance_id: AmbulanceId
    hospital_id: HospitalId


class CSPTraceStep(BaseModel):
    step: int
    variable: EmergencyId
    value: str
    outcome: Literal["ASSIGN", "REJECT", "BACKTRACK", "PRUNE"]
    reason: str


class CSPResult(BaseModel):
    """Output of the CSP solver (Phase 7)."""

    status: Literal["SOLVED", "PARTIAL", "UNSATISFIABLE"]
    assignments: dict[EmergencyId, CSPAssignment] = Field(default_factory=dict)
    unassigned: dict[EmergencyId, str] = Field(
        default_factory=dict, description="Emergency id -> reason code."
    )
    constraints_checked: int = 0
    conflicts: int = 0
    backtracks: int = 0
    domain_reductions: int = 0
    execution_ms: float = 0.0
    trace: list[CSPTraceStep] = Field(default_factory=list)


class HMMResult(BaseModel):
    """Output of the HMM forward algorithm (Phase 5)."""

    belief: dict[FloodState, float]
    most_likely: FloodState
    observation_history: list[Observation] = Field(default_factory=list)
    belief_history: list[list[float]] = Field(
        default_factory=list, description="One row per tick, ordered as FloodState."
    )
    execution_ms: float = 0.0


class BayesResult(BaseModel):
    """Output of Bayesian Network inference (Phase 5)."""

    query: str
    probability: float = Field(ge=0.0, le=1.0)
    evidence: dict[str, str] = Field(default_factory=dict)
    per_road: dict[RoadId, float] = Field(default_factory=dict)
    marginals: dict[str, dict[str, float]] = Field(default_factory=dict)
    used_hmm_virtual_evidence: bool = True
    execution_ms: float = 0.0


class InferenceStep(BaseModel):
    rule_name: str
    bindings: dict[str, str]
    premises: list[str]
    conclusion: str


class InferenceResult(BaseModel):
    """Output of forward chaining (Phase 6)."""

    initial_facts: list[str] = Field(default_factory=list)
    derived_facts: list[str] = Field(default_factory=list)
    steps: list[InferenceStep] = Field(default_factory=list)
    iterations: int = 0
    execution_ms: float = 0.0


class FOLResult(BaseModel):
    """Output of a conjunctive first-order query (Phase 6)."""

    query: str
    bindings: list[dict[str, str]] = Field(default_factory=list)
    count: int = 0
    execution_ms: float = 0.0


class PlanAction(BaseModel):
    name: str
    args: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    add_effects: list[str] = Field(default_factory=list)
    delete_effects: list[str] = Field(default_factory=list)


class PlanNode(BaseModel):
    """A node in the HTN decomposition tree."""

    task: str
    method: str | None = None
    primitive: bool = False
    children: list["PlanNode"] = Field(default_factory=list)


class PlanResult(BaseModel):
    """Output of the classical + hierarchical planner (Phase 8)."""

    status: Literal["FOUND", "NO_PLAN"]
    goal: str
    actions: list[PlanAction] = Field(default_factory=list)
    hierarchy: PlanNode | None = None
    plan_length: int = 0
    nodes_expanded: int = 0
    execution_ms: float = 0.0
    invalidated_step: int | None = Field(
        default=None, description="Index of the first step whose preconditions broke."
    )
