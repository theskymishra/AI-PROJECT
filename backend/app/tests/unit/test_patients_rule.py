"""Tests for the deterministic patients derivation rule.

    patients = min(people_affected, 1 + medical_priority // 2)
    clamped to [1, MAX_AMBULANCE_CAPACITY]

Invariants enforced:
    1 <= patients <= people_affected
    patients <= MAX_AMBULANCE_CAPACITY
"""

import pytest

from app.models.common import MAX_AMBULANCE_CAPACITY, Severity
from app.models.emergency import Emergency, derive_patients


@pytest.mark.parametrize(
    "priority,expected",
    [(1, 1), (2, 2), (3, 2), (4, 3), (5, 3)],
)
def test_rule_maps_priority_to_expected_patient_count(priority, expected):
    assert derive_patients(people_affected=10, medical_priority=priority) == expected


def test_people_affected_caps_the_result():
    # priority 5 would give 3, but only one person is present.
    assert derive_patients(people_affected=1, medical_priority=5) == 1


def test_result_never_exceeds_max_ambulance_capacity():
    for priority in range(1, 6):
        for people in range(1, 60):
            assert (
                derive_patients(people, priority) <= MAX_AMBULANCE_CAPACITY
            ), f"priority={priority} people={people}"


def test_result_is_always_at_least_one():
    for priority in range(1, 6):
        for people in range(1, 60):
            assert derive_patients(people, priority) >= 1


def test_result_never_exceeds_people_affected():
    for priority in range(1, 6):
        for people in range(1, 60):
            assert derive_patients(people, priority) <= people


def test_rule_is_deterministic():
    values = {derive_patients(17, 4) for _ in range(1000)}
    assert values == {3}


def test_rejects_zero_people():
    with pytest.raises(ValueError, match="people_affected must be >= 1"):
        derive_patients(0, 3)


@pytest.mark.parametrize("priority", [0, 6, -1, 99])
def test_rejects_out_of_range_priority(priority):
    with pytest.raises(ValueError, match="medical_priority must be in"):
        derive_patients(5, priority)


def test_create_derives_patients_from_priority():
    emergency = Emergency.create(
        id="E7",
        node_id="N12",
        zone_id="Z1",
        severity=Severity.CRITICAL,
        people_affected=9,
        medical_priority=5,
        reported_at_tick=180,
    )
    assert emergency.patients == 3
    assert emergency.people_affected == 9


def test_model_rejects_patients_exceeding_people_affected():
    with pytest.raises(ValueError, match="exceeds people_affected"):
        Emergency(
            id="E1",
            node_id="N1",
            zone_id="Z1",
            severity=Severity.HIGH,
            people_affected=2,
            patients=3,
            medical_priority=4,
            reported_at_tick=0,
        )


def test_model_rejects_patients_above_fleet_capacity():
    with pytest.raises(ValueError):
        Emergency(
            id="E1",
            node_id="N1",
            zone_id="Z1",
            severity=Severity.CRITICAL,
            people_affected=20,
            patients=MAX_AMBULANCE_CAPACITY + 1,
            medical_priority=5,
            reported_at_tick=0,
        )


def test_three_patient_emergency_would_exclude_capacity_two_ambulances():
    """The pruning property Phase 7 depends on."""
    patients = derive_patients(people_affected=8, medical_priority=4)
    fleet_capacities = [2, 2, 4, 4]
    eligible = [c for c in fleet_capacities if c >= patients]
    assert patients == 3
    assert eligible == [4, 4], "domain should shrink from 4 ambulances to 2"
