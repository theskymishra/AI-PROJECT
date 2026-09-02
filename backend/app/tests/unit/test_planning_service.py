from __future__ import annotations

from types import SimpleNamespace

from app.services.planning_service import HTNPlanner


def _state(emergencies):
    return SimpleNamespace(
        emergencies={e.id: e for e in emergencies},
        ambulances={"A1": SimpleNamespace(id="A1")},
        hospitals={"H1": SimpleNamespace(id="H1")},
    )


def test_planner_returns_no_plan_without_assigned_emergency():
    emergency = SimpleNamespace(
        id="E1", status="ACTIVE", assigned_ambulance=None, assigned_hospital=None,
        medical_priority=3, waiting_ticks=2,
    )
    result = HTNPlanner().plan(_state([emergency]))
    assert result.status == "NO_PLAN"
    assert result.actions == []


def test_planner_decomposes_assigned_emergency():
    emergency = SimpleNamespace(
        id="E1", status="ALLOCATED", assigned_ambulance="A1", assigned_hospital="H1",
        medical_priority=3, waiting_ticks=2,
    )
    result = HTNPlanner().plan(_state([emergency]))
    assert result.status == "FOUND"
    assert result.plan_length == 4
    assert [a.name for a in result.actions] == [
        "DISPATCH_AMBULANCE", "LOAD_PATIENTS", "TRANSPORT_TO_HOSPITAL", "HANDOFF_PATIENTS"
    ]
    assert result.hierarchy is not None
    assert result.hierarchy.children[0].task == "RESCUE(E1)"
    assert result.hierarchy.children[0].children[0].primitive is True
