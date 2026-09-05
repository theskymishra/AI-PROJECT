"""Phase 11 monitoring unit tests."""
from __future__ import annotations

from app.models.ambulance import Ambulance
from app.models.common import AmbulanceStatus, EmergencyStatus
from app.models.emergency import Emergency
from app.services.monitoring_service import ResponseMonitoringService
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


def test_monitoring_empty_state_is_clear() -> None:
    state = WorldState.create("NORMAL", build_world())
    result = ResponseMonitoringService().assess(state)
    assert result.overall == "CLEAR"
    assert result.health.active_emergencies == 0


def test_monitoring_detects_unassigned_emergency() -> None:
    state = WorldState.create("NORMAL", build_world())
    emergency = Emergency.create(
        id="E99",
        node_id="N1",
        zone_id="Z1",
        severity="HIGH",
        people_affected=2,
        medical_priority=2,
        reported_at_tick=0,
    )
    state.emergencies[emergency.id] = emergency
    result = ResponseMonitoringService().assess(state)
    assert result.replanning_required is True
    assert result.items[0].attention == "UNASSIGNED"


def test_monitoring_assigned_emergency_is_ready() -> None:
    state = make_state()
    result = ResponseMonitoringService().assess(state)
    assert result.replanning_required is False
    assert result.items[0].attention == "READY"
    assert result.health.assigned_emergencies == 1


def test_monitoring_is_read_only() -> None:
    state = make_state()

    before_emergencies = repr(state.emergencies)
    before_ambulances = repr(state.ambulances)
    before_hospitals = repr(state.hospitals)

    ResponseMonitoringService().assess(state, include_plan=True)

    assert repr(state.emergencies) == before_emergencies
    assert repr(state.ambulances) == before_ambulances
    assert repr(state.hospitals) == before_hospitals