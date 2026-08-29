"""Road model.

WORLD INVARIANT W1
------------------
    distance >= geometric_length

The A* heuristic h(n) = SCALE_KM_PER_UNIT * euclid(n, goal) is admissible only
if every road is at least as long as the straight line between its endpoints.
Violate W1 and A* returns suboptimal paths while reporting them as optimal --
a silent correctness bug no amount of UI review would surface.

The invariant is enforced here at the type boundary, and additionally asserted
against the whole graph by tests/unit/test_world_invariants.py once the world
builder exists in Phase 2. Road lengths are computed from node coordinates at
world-build time, never hand-authored.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, model_validator

from app.models.common import ElevationBand, NodeId, RoadId, RoadStatus

#: Failure probability at or above which a road is displayed as RISKY.
RISKY_THRESHOLD = 0.45

#: Floating-point slack when comparing distance against geometric_length.
_W1_TOLERANCE = 1e-9


class Road(BaseModel):
    """A bidirectional road segment between two nodes."""

    id: RoadId
    source: NodeId
    destination: NodeId

    distance: float = Field(
        gt=0, description="Road length in kilometres. Subject to invariant W1."
    )
    geometric_length: float = Field(
        gt=0,
        description=(
            "SCALE_KM_PER_UNIT * euclidean(source, destination), in kilometres. "
            "Derived at world-build time."
        ),
    )
    detour_factor: float = Field(
        ge=1.0,
        description="distance / geometric_length. Roads bend, so this is >= 1.",
    )

    elevation_band: ElevationBand = Field(
        description=(
            "Static terrain band. Parent of the SurfaceWater node in the "
            "Bayesian Network (Phase 5)."
        )
    )

    flood_level: float = Field(default=0.0, ge=0.0, le=1.0)
    damage_level: float = Field(default=0.0, ge=0.0, le=1.0)

    failure_probability: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="P(RoadFailure = TRUE) from the Bayesian Network (Phase 5).",
    )
    risk_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Composite display-only figure. Never an input to A*.",
    )

    blocked: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> RoadStatus:
        """Derived road status.

        Computed, not stored -- but it IS serialised. The frontend renders road
        state on the map, and reimplementing the threshold in TypeScript would
        put the same rule in two languages where they can drift apart.
        """
        if self.blocked:
            return RoadStatus.BLOCKED
        if self.failure_probability >= RISKY_THRESHOLD:
            return RoadStatus.RISKY
        return RoadStatus.SAFE

    @property
    def base_cost(self) -> float:
        """Un-weighted edge cost, identical to ``distance``.

        Retained because the project brief names it. The A* cost multiplier is
        applied to this value: w(e) = base_cost * (1 + a*flood + b*damage + g*Pfail).
        """
        return self.distance

    @model_validator(mode="after")
    def _check_w1(self) -> "Road":
        if self.distance + _W1_TOLERANCE < self.geometric_length:
            raise ValueError(
                f"Road {self.id} violates world invariant W1: "
                f"distance={self.distance} < geometric_length="
                f"{self.geometric_length}. The A* heuristic would no longer be "
                f"admissible."
            )
        return self
