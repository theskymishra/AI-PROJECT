"""Phase 10 execution unit tests."""
from __future__ import annotations

from app.models.ambulance import Ambulance
from app.models.common import AmbulanceStatus, EmergencyStatus
from app.models.emergency import Emergency
from app.models.planning import PlanAction
from app.models.hospital import Hospital
from app.services.execution_service import ExecutionError, PlanExecutionService
from app.simulation.state import WorldState
from app.simulation.world import build_world


def make_state() -> WorldState:
    state = WorldState.create("NORMAL", build_world())
    emergency = Emergency.create(
        id="E1",
        node_id="N1",
        zone_id="Z1",
        severity="HIGH",
        people_affected=3,
        medical_priority=3,
        reported_at_tick=0,
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


def test_prepare_without_assignments_returns_no_plan() -> None:
    state = WorldState.create("NORMAL", build_world())
    service = PlanExecutionService()
    result = service.prepare(state)
    assert result.status == "NO_PLAN"
    assert result.total_actions == 0


def test_action_sequence_mutates_expected_state() -> None:
    state = make_state()
    service = PlanExecutionService()
    service._plan = [
        PlanAction(name="DISPATCH_AMBULANCE", args=["A1", "E1"]),
        PlanAction(name="LOAD_PATIENTS", args=["A1", "E1"]),
        PlanAction(name="TRANSPORT_TO_HOSPITAL", args=["A1", "E1", "H1"]),
        PlanAction(name="HANDOFF_PATIENTS", args=["E1", "H1"]),
    ]
    service._signature = service._assignment_signature(state)

    service._apply_action(state, service._plan[0])
    assert state.emergencies["E1"].status == EmergencyStatus.EN_ROUTE
    assert state.ambulances["A1"].status == AmbulanceStatus.EN_ROUTE

    service._apply_action(state, service._plan[1])
    assert state.emergencies["E1"].status == EmergencyStatus.ON_SCENE
    assert state.ambulances["A1"].status == AmbulanceStatus.AT_SCENE

    service._apply_action(state, service._plan[2])
    assert state.emergencies["E1"].status == EmergencyStatus.TRANSPORTING
    assert state.ambulances["A1"].status == AmbulanceStatus.TRANSPORTING

    service._apply_action(state, service._plan[3])
    assert state.emergencies["E1"].status == EmergencyStatus.RESOLVED
    assert state.ambulances["A1"].status == AmbulanceStatus.AVAILABLE
    assert state.ambulances["A1"].assigned_emergency is None


def test_stale_assignment_is_rejected() -> None:
    state = make_state()
    service = PlanExecutionService()
    service._plan = [PlanAction(name="DISPATCH_AMBULANCE", args=["A1", "E1"])]
    service._signature = service._assignment_signature(state)
    state.emergencies["E1"].assigned_hospital = None
    try:
        service._ensure_plan_current(state)
    except ExecutionError:
        return
    raise AssertionError("Expected stale execution plan to be rejected")
