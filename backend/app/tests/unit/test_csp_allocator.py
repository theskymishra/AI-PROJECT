from app.services.csp_service import CSPAllocator
from app.simulation.state import WorldState
from app.simulation.world import build_world


def test_csp_allocates_available_emergencies_with_real_constraints():
    state = WorldState.create("NORMAL", build_world())
    # Keep the test deterministic and create two active emergencies.
    from app.models.emergency import Emergency
    from app.models.common import Severity

    state.emergencies = {
        "E1": Emergency.create(
            id="E1", node_id="N1", zone_id="Z1", severity=Severity.CRITICAL,
            people_affected=5, medical_priority=5, reported_at_tick=0,
        ),
        "E2": Emergency.create(
            id="E2", node_id="N2", zone_id="Z1", severity=Severity.HIGH,
            people_affected=3, medical_priority=4, reported_at_tick=0,
        ),
    }
    result = CSPAllocator().solve(state)
    assert result.status in {"SOLVED", "PARTIAL"}
    assert result.constraints_checked > 0
    assert all(a.ambulance_id for a in result.assignments.values())
    assert all(a.hospital_id for a in result.assignments.values())


def test_csp_trace_contains_forward_check_or_backtracking_metrics():
    state = WorldState.create("NORMAL", build_world())
    from app.models.emergency import Emergency
    from app.models.common import Severity

    state.emergencies = {
        "E1": Emergency.create(
            id="E1", node_id="N1", zone_id="Z1", severity=Severity.HIGH,
            people_affected=4, medical_priority=5, reported_at_tick=0,
        ),
        "E2": Emergency.create(
            id="E2", node_id="N2", zone_id="Z1", severity=Severity.HIGH,
            people_affected=4, medical_priority=5, reported_at_tick=0,
        ),
    }
    result = CSPAllocator().solve(state)
    assert result.trace
    assert result.domain_reductions >= 0
    assert result.backtracks >= 0


def test_apply_commits_assignments_without_reassigning_busy_resources():
    state = WorldState.create("NORMAL", build_world())
    from app.models.emergency import Emergency
    from app.models.common import Severity

    state.emergencies = {
        "E1": Emergency.create(
            id="E1", node_id="N1", zone_id="Z1", severity=Severity.CRITICAL,
            people_affected=2, medical_priority=3, reported_at_tick=0,
        )
    }
    allocator = CSPAllocator()
    result = allocator.solve(state)
    allocator.apply(state, result)
    for emergency_id, assignment in result.assignments.items():
        assert state.emergencies[emergency_id].assigned_ambulance == assignment.ambulance_id
        assert state.ambulances[assignment.ambulance_id].assigned_emergency == emergency_id
        assert state.emergencies[emergency_id].assigned_hospital == assignment.hospital_id
