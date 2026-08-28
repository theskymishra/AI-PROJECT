"""Emergency model and the deterministic ``patients`` derivation rule.

WHY ``patients`` EXISTS SEPARATELY FROM ``people_affected``
----------------------------------------------------------
The CSP capacity constraint is ``ambulance.capacity >= emergency.patients``.
The fleet has capacities 2, 2, 4, 4. If that constraint bound against
``people_affected`` instead, any emergency involving five or more people would
have an empty domain and the solver would return UNSATISFIABLE mid-demo.

So the two counts mean different things:

    people_affected  total people at the scene; drives evacuation and
                     shelter-occupancy figures
    patients         the subset requiring ambulance transport; the only
                     quantity the capacity constraint looks at

PHASE NOTE
----------
``derive_patients`` is the canonical implementation of the rule. The scenario
generator introduced in Phase 2 (app/simulation/scenarios.py) must call this
function rather than reimplementing the arithmetic, so that the rule has exactly
one definition.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.models.common import (
    MAX_AMBULANCE_CAPACITY,
    MAX_MEDICAL_PRIORITY,
    MIN_MEDICAL_PRIORITY,
    AmbulanceId,
    EmergencyId,
    EmergencyStatus,
    HospitalId,
    NodeId,
    Severity,
    ZoneId,
)


def derive_patients(people_affected: int, medical_priority: int) -> int:
    """Deterministically derive the transport load for an emergency.

        patients = min(people_affected, 1 + medical_priority // 2)

    then clamped to [1, MAX_AMBULANCE_CAPACITY].

    Deterministic by construction: a pure function of two integers, no RNG, no
    clock, no global state. Two runs of the same scenario produce the same
    patient counts, which is a precondition for the reproducibility guarantee in
    Phase 0 section 3.

    Resulting distribution over medical_priority (given enough people present):

        priority 1 -> 1 patient
        priority 2 -> 2 patients
        priority 3 -> 2 patients
        priority 4 -> 3 patients
        priority 5 -> 3 patients

    Note the rule never yields 4. A 3-patient emergency already eliminates the
    two capacity-2 ambulances, which is what gives AC-3 and backtracking real
    domain reductions in Phase 7. If Phase 7 needs tighter instances than that,
    the rule -- not the constraint -- is the thing to change, and it should be
    changed here.

    Args:
        people_affected: Total people at the scene. Must be >= 1.
        medical_priority: Clinical urgency, 1 (lowest) to 5 (highest).

    Returns:
        Patient count in [1, min(people_affected, MAX_AMBULANCE_CAPACITY)].

    Raises:
        ValueError: If either argument is outside its documented range.
    """
    if people_affected < 1:
        raise ValueError(f"people_affected must be >= 1, got {people_affected}")
    if not MIN_MEDICAL_PRIORITY <= medical_priority <= MAX_MEDICAL_PRIORITY:
        raise ValueError(
            f"medical_priority must be in "
            f"[{MIN_MEDICAL_PRIORITY}, {MAX_MEDICAL_PRIORITY}], "
            f"got {medical_priority}"
        )

    raw = 1 + medical_priority // 2
    return max(1, min(raw, people_affected, MAX_AMBULANCE_CAPACITY))


class Emergency(BaseModel):
    """A reported incident requiring rescue and medical transport."""

    id: EmergencyId
    node_id: NodeId
    zone_id: ZoneId
    severity: Severity

    people_affected: int = Field(
        ge=1, description="Total people at the scene."
    )
    patients: int = Field(
        ge=1,
        le=MAX_AMBULANCE_CAPACITY,
        description=(
            "Subset of people_affected requiring ambulance transport. "
            "Derived by derive_patients(); the CSP capacity constraint binds "
            "against this field."
        ),
    )
    medical_priority: int = Field(
        ge=MIN_MEDICAL_PRIORITY, le=MAX_MEDICAL_PRIORITY
    )

    reported_at_tick: int = Field(ge=0)
    waiting_ticks: int = Field(default=0, ge=0)
    status: EmergencyStatus = EmergencyStatus.REPORTED

    assigned_ambulance: AmbulanceId | None = None
    assigned_hospital: HospitalId | None = None

    @model_validator(mode="after")
    def _check_invariants(self) -> "Emergency":
        # INVARIANT: 1 <= patients <= people_affected
        if self.patients > self.people_affected:
            raise ValueError(
                f"patients ({self.patients}) exceeds people_affected "
                f"({self.people_affected}) for emergency {self.id}"
            )
        # INVARIANT: patients <= max(ambulance.capacity)
        # Enforced by the Field constraint above; restated here so the
        # invariant is visible in one place.
        if self.patients > MAX_AMBULANCE_CAPACITY:
            raise ValueError(
                f"patients ({self.patients}) exceeds MAX_AMBULANCE_CAPACITY "
                f"({MAX_AMBULANCE_CAPACITY}) for emergency {self.id}"
            )
        return self

    @classmethod
    def create(
        cls,
        *,
        id: EmergencyId,
        node_id: NodeId,
        zone_id: ZoneId,
        severity: Severity,
        people_affected: int,
        medical_priority: int,
        reported_at_tick: int,
    ) -> "Emergency":
        """Construct an Emergency with ``patients`` derived, not supplied.

        This is the constructor scenario code should use. Passing ``patients``
        explicitly to ``Emergency(...)`` is allowed (deserialisation needs it)
        but bypasses the rule.
        """
        return cls(
            id=id,
            node_id=node_id,
            zone_id=zone_id,
            severity=severity,
            people_affected=people_affected,
            patients=derive_patients(people_affected, medical_priority),
            medical_priority=medical_priority,
            reported_at_tick=reported_at_tick,
        )
