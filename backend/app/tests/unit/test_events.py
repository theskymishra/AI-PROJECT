"""Event application and error handling."""

import pytest

from app.models.common import AlertLevel, Severity
from app.models.events import SimEvent
from app.simulation.events import EventError, apply_event
from app.simulation.state import WorldState


def _state():
    return WorldState.create("SEVERE_FLOOD")


def _apply(state, type_, **payload):
    return apply_event(state, SimEvent(tick=state.clock.tick, type=type_, payload=payload))


def test_blocking_a_road_sets_the_flag_and_logs_the_timeline():
    state = _state()
    outcome = _apply(state, "ROAD_BLOCKED", road_id="R17")
    assert state.roads["R17"].blocked is True
    assert outcome.roads_changed == ("R17",)
    assert state.timeline[-1].headline == "ROAD R17 BLOCKED"
    assert state.alerts[-1].level is AlertLevel.CRITICAL


def test_blocking_an_already_blocked_road_is_rejected():
    state = _state()
    _apply(state, "ROAD_BLOCKED", road_id="R17")
    with pytest.raises(EventError, match="already blocked"):
        _apply(state, "ROAD_BLOCKED", road_id="R17")


def test_restoring_an_open_road_is_rejected():
    with pytest.raises(EventError, match="not blocked"):
        _apply(_state(), "ROAD_RESTORED", road_id="R17")


def test_unknown_road_is_rejected():
    with pytest.raises(EventError, match="unknown road"):
        _apply(_state(), "ROAD_BLOCKED", road_id="R999")


def test_unknown_event_type_is_rejected():
    state = _state()
    with pytest.raises(EventError, match="unknown event type"):
        apply_event(state, SimEvent(tick=0, type="ROUTE_UPDATED", payload={}))


def test_road_restore_reverses_a_block():
    state = _state()
    _apply(state, "ROAD_BLOCKED", road_id="R17")
    _apply(state, "ROAD_RESTORED", road_id="R17")
    assert state.roads["R17"].blocked is False


def test_rainfall_change_sets_a_target_not_the_value():
    """Targets ramp. A step change would make the sensor chart a staircase."""
    state = _state()
    before = state.environment.rainfall_mm
    _apply(state, "RAINFALL_CHANGE", target_mm=30.0)
    assert state.environment.rainfall_target_mm == 30.0
    assert state.environment.rainfall_mm == before


def test_water_level_change_sets_a_target():
    state = _state()
    _apply(state, "WATER_LEVEL_CHANGE", target_m=3.2)
    assert state.environment.water_target_m == 3.2


def test_negative_targets_are_rejected():
    with pytest.raises(EventError):
        _apply(_state(), "WATER_LEVEL_CHANGE", target_m=-1.0)


def test_emergency_creation_derives_patients():
    state = _state()
    _apply(
        state, "EMERGENCY_CREATED", id="E7", node_id="N1",
        severity="CRITICAL", people_affected=9, medical_priority=5,
    )
    emergency = state.emergencies["E7"]
    assert emergency.patients == 3          # 1 + 5 // 2
    assert emergency.people_affected == 9
    assert emergency.zone_id == "Z1"        # inferred from the node
    assert emergency.severity is Severity.CRITICAL


def test_duplicate_emergency_id_is_rejected():
    state = _state()
    payload = dict(id="E7", node_id="N1", severity="HIGH",
                   people_affected=4, medical_priority=3)
    _apply(state, "EMERGENCY_CREATED", **payload)
    with pytest.raises(EventError, match="already exists"):
        _apply(state, "EMERGENCY_CREATED", **payload)


def test_emergency_at_an_unknown_node_is_rejected():
    with pytest.raises(EventError, match="unknown node"):
        _apply(_state(), "EMERGENCY_CREATED", id="E9", node_id="N999",
               severity="LOW", people_affected=1, medical_priority=1)


def test_hospital_overload_reduces_capacity_and_changes_status():
    state = _state()
    _apply(state, "HOSPITAL_OVERLOAD", hospital_id="H2",
           available_beds=0, available_icu=0)
    assert state.hospitals["H2"].available_beds == 0
    assert state.hospitals["H2"].status.value == "FULL"


def test_overload_above_capacity_is_rejected():
    with pytest.raises(EventError, match="above capacity"):
        _apply(_state(), "HOSPITAL_OVERLOAD", hospital_id="H2",
               available_beds=9999, available_icu=0)


def test_road_damage_is_clamped_to_the_unit_interval():
    with pytest.raises(EventError, match=r"\[0, 1\]"):
        _apply(_state(), "ROAD_DAMAGE", road_id="R17", damage_level=1.5)


def test_every_applied_event_produces_a_timeline_entry():
    state = _state()
    _apply(state, "RAINFALL_CHANGE", target_mm=10.0)
    _apply(state, "WATER_LEVEL_CHANGE", target_m=2.0)
    _apply(state, "ROAD_BLOCKED", road_id="R17")
    assert len(state.timeline) == 3
    assert [t.category for t in state.timeline] == ["WEATHER", "WATER", "ROAD"]


def test_only_notable_events_raise_alerts():
    state = _state()
    _apply(state, "RAINFALL_CHANGE", target_mm=5.0)   # mild, no alert
    assert state.alerts == []
    _apply(state, "ROAD_BLOCKED", road_id="R17")      # critical
    assert len(state.alerts) == 1
