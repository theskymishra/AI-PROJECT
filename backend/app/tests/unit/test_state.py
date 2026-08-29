"""WorldState, and the epsilon guard on environment_version."""

import pytest

from app.config import RISK_EPSILON
from app.models.common import SimStatus
from app.simulation.state import WorldState


def _state():
    return WorldState.create("SEVERE_FLOOD")


def test_fresh_state_is_idle_at_version_zero():
    state = _state()
    assert state.clock.status is SimStatus.IDLE
    assert state.clock.tick == 0
    assert state.environment_version == 0


def test_state_copies_the_world_rather_than_aliasing_it():
    """A run must not be able to corrupt the static world."""
    state = _state()
    state.roads["R17"].blocked = True
    assert state.world.road_by_id["R17"].blocked is False
    assert WorldState.create("SEVERE_FLOOD").roads["R17"].blocked is False


def test_blocking_a_road_bumps_the_version():
    state = _state()
    before = state.environment_version
    state.roads["R17"].blocked = True
    changed = state.reconcile_environment_version()
    assert changed == ["R17"]
    assert state.environment_version == before + 1


def test_restoring_a_road_bumps_the_version():
    state = _state()
    state.roads["R17"].blocked = True
    state.reconcile_environment_version()
    before = state.environment_version
    state.roads["R17"].blocked = False
    state.reconcile_environment_version()
    assert state.environment_version == before + 1


def test_no_change_does_not_bump_the_version():
    state = _state()
    for _ in range(50):
        assert state.reconcile_environment_version() == []
    assert state.environment_version == 0


def test_sub_epsilon_flood_drift_does_not_bump_the_version():
    """THE PHASE 0 CORRECTION.

    Flood level moves a little every tick while water rises. Under the rule as
    originally written -- 'any flood_level change bumps' -- the version would
    increment on every tick and the Phase 4 route cache would never serve one
    hit. The epsilon must govern this field too.
    """
    state = _state()
    road = state.roads["R17"]
    # Five steps of EPSILON/10 is half an epsilon of total drift.
    for _ in range(5):
        road.flood_level = min(1.0, road.flood_level + RISK_EPSILON / 10)
        state.reconcile_environment_version()
    assert state.environment_version == 0, (
        "sub-epsilon drift bumped the version; the route cache would be useless"
    )


def test_flood_change_at_or_above_epsilon_does_bump():
    state = _state()
    state.roads["R17"].flood_level += RISK_EPSILON
    state.reconcile_environment_version()
    assert state.environment_version == 1


def test_damage_change_at_or_above_epsilon_bumps():
    state = _state()
    state.roads["R17"].damage_level += RISK_EPSILON
    state.reconcile_environment_version()
    assert state.environment_version == 1


def test_failure_probability_change_at_or_above_epsilon_bumps():
    """Phase 5 will drive this field; the guard must already be in place."""
    state = _state()
    state.roads["R17"].failure_probability += RISK_EPSILON
    state.reconcile_environment_version()
    assert state.environment_version == 1


def test_a_full_flood_rise_bumps_a_handful_of_times_not_once_per_tick():
    """The real-world shape of the Phase 0 correction.

    Flooding a road from dry to 0.8 must cost a bounded number of cache
    invalidations, not one per tick. At EPSILON = 0.05 that is about 16.
    """
    state = _state()
    road = state.roads["R17"]
    ticks = 400
    for i in range(ticks):
        road.flood_level = min(0.8, road.flood_level + 0.8 / ticks)
        state.reconcile_environment_version()
    assert state.environment_version <= 20, (
        f"{state.environment_version} bumps over {ticks} ticks"
    )
    assert state.environment_version >= 10, "epsilon is so coarse it never fires"


def test_accumulated_drift_eventually_crosses_the_epsilon():
    """Sub-epsilon steps must not be ignored forever -- only until they add up."""
    state = _state()
    road = state.roads["R17"]
    for _ in range(30):
        road.flood_level = min(1.0, road.flood_level + RISK_EPSILON / 4)
        state.reconcile_environment_version()
    assert state.environment_version >= 5


def test_one_bump_per_reconcile_regardless_of_how_many_roads_changed():
    state = _state()
    for rid in ("R1", "R2", "R3"):
        state.roads[rid].blocked = True
    changed = state.reconcile_environment_version()
    assert set(changed) == {"R1", "R2", "R3"}
    assert state.environment_version == 1


def test_emergencies_and_capacity_never_bump_the_version():
    from app.models.common import Severity
    from app.models.emergency import Emergency

    state = _state()
    state.emergencies["E1"] = Emergency.create(
        id="E1", node_id="N1", zone_id="Z1", severity=Severity.HIGH,
        people_affected=5, medical_priority=4, reported_at_tick=0,
    )
    state.hospitals["H1"].available_beds = 1
    state.reconcile_environment_version()
    assert state.environment_version == 0


# -- stats -----------------------------------------------------------------


def test_stats_count_real_things():
    state = _state()
    stats = state.stats()
    assert stats["total_ambulances"] == 4
    assert stats["available_ambulances"] == 4
    assert stats["total_roads"] == 38
    assert stats["blocked_roads"] == 0
    assert stats["active_emergencies"] == 0
    assert stats["total_beds"] == 48 + 24 + 36


def test_blocked_road_count_tracks_state():
    state = _state()
    state.roads["R17"].blocked = True
    assert state.stats()["blocked_roads"] == 1


def test_people_at_risk_sums_active_emergencies_only():
    from app.models.common import EmergencyStatus, Severity
    from app.models.emergency import Emergency

    state = _state()
    state.emergencies["E1"] = Emergency.create(
        id="E1", node_id="N1", zone_id="Z1", severity=Severity.HIGH,
        people_affected=9, medical_priority=4, reported_at_tick=0,
    )
    state.emergencies["E2"] = Emergency.create(
        id="E2", node_id="N2", zone_id="Z1", severity=Severity.LOW,
        people_affected=3, medical_priority=1, reported_at_tick=0,
    )
    state.emergencies["E2"].status = EmergencyStatus.RESOLVED
    stats = state.stats()
    assert stats["active_emergencies"] == 1
    assert stats["people_at_risk"] == 9


def test_seq_is_monotonic():
    state = _state()
    assert [state.next_seq() for _ in range(3)] == [1, 2, 3]


def test_timeline_and_alerts_are_bounded():
    from app.config import MAX_ALERTS, MAX_TIMELINE_ENTRIES
    from app.models.common import AlertLevel
    from app.models.events import Alert, TimelineEntry

    state = _state()
    for i in range(MAX_TIMELINE_ENTRIES + 40):
        state.add_timeline(
            TimelineEntry(id=f"T{i}", tick=i, category="X", headline="h", detail="d")
        )
        state.add_alert(
            Alert(id=f"A{i}", tick=i, level=AlertLevel.INFO, title="t",
                  message="m", source="test")
        )
    assert len(state.timeline) == MAX_TIMELINE_ENTRIES
    assert len(state.alerts) == MAX_ALERTS
    # Newest kept, oldest dropped.
    assert state.timeline[-1].id == f"T{MAX_TIMELINE_ENTRIES + 39}"
