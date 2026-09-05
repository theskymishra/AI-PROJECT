"""Phase 12 decision explainability unit tests."""
from __future__ import annotations

from app.models.ambulance import Ambulance
from app.models.common import AmbulanceStatus, EmergencyStatus
from app.models.emergency import Emergency
from app.models.hospital import Hospital
from app.services.explainability_service import DecisionExplainabilityService
from app.simulation.state import WorldState
from app.simulation.world import build_world


def make_state() -> WorldState:
    state = WorldState.create("NORMAL", build_world())
    emergency = Emergency.create(
        id="E1", node_id="N1", zone_id="Z1", severity="HIGH",
        people_affected=3, medical_priority=3, reported_at_tick=0,
    )
    ambulance = next(a for a in state.ambulances.values() if a.id == "A1").model_copy(deep=True)
    hospital = next(iter(state.hospitals.values())).model_copy(deep=True)
    emergency.assigned_ambulance = ambulance.id
    emergency.assigned_hospital = hospital.id
    emergency.status = EmergencyStatus.ALLOCATED
    ambulance.assigned_emergency = emergency.id
    ambulance.status = AmbulanceStatus.DISPATCHED
    hospital.available_beds -= emergency.patients
    state.emergencies[emergency.id] = emergency
    state.ambulances[ambulance.id] = ambulance
    state.hospitals[hospital.id] = hospital
    return state


def test_report_explains_assigned_emergency() -> None:
    result = DecisionExplainabilityService().build_report(make_state())
    assert result.status == "OK"
    assert result.explanations[0].emergency_id == "E1"
    assert result.explanations[0].ambulance_id == "A1"
    assert result.explanations[0].hospital_id is not None
    assert len(result.explanations[0].steps) == 4
    assert result.plan_status == "FOUND"
    assert result.plan_length == 4


def test_report_is_read_only() -> None:
    state = make_state()
    before = (
        repr(state.emergencies),
        repr(state.ambulances),
        repr(state.hospitals),
        repr(state.timeline),
        state.clock.tick,
    )
    DecisionExplainabilityService().build_report(state)
    after = (
        repr(state.emergencies),
        repr(state.ambulances),
        repr(state.hospitals),
        repr(state.timeline),
        state.clock.tick,
    )
    assert after == before
