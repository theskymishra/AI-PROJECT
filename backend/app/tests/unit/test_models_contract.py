"""Contract tests for the frozen data models.

Phase 1 freezes the shapes; Phase 2 onward fills them with real data. These
tests prove every model constructs, serialises to JSON, and round-trips back
without loss -- which is what the frontend contract depends on.

Agreement between these Pydantic models and frontend/src/types/index.ts is
enforced by review, not by tooling. The two files must change together.
"""

import json

import pytest

from app.models import (
    Alert,
    AlertLevel,
    Ambulance,
    AmbulanceStatus,
    BayesResult,
    CSPAssignment,
    CSPResult,
    ElevationBand,
    Emergency,
    FloodState,
    Hospital,
    HMMResult,
    InferenceResult,
    Node,
    NodeKind,
    Observation,
    PlanNode,
    PlanResult,
    Road,
    RoadStatus,
    RouteResult,
    SensorReading,
    Severity,
    Shelter,
    SimEvent,
    SSEEnvelope,
    TimelineEntry,
    Zone,
)


def _round_trip(model):
    """Serialise to JSON and parse back; assert equality."""
    restored = type(model).model_validate(json.loads(model.model_dump_json()))
    assert restored == model
    return restored


SAMPLES = [
    Node(id="N1", name="Riverside Junction", x=120, y=480, zone_id="Z1",
         kind=NodeKind.JUNCTION),
    Zone(id="Z1", name="Riverside", polygon=[(0, 400), (300, 400), (300, 700), (0, 700)],
         population=12000, elevation=0.15, elevation_band=ElevationBand.LOW),
    Road(id="R17", source="N1", destination="N2", distance=4.2, geometric_length=3.5,
         detour_factor=1.2, elevation_band=ElevationBand.LOW),
    Emergency.create(id="E7", node_id="N1", zone_id="Z1", severity=Severity.CRITICAL,
                     people_affected=9, medical_priority=5, reported_at_tick=180),
    Ambulance(id="A1", node_id="N3", capacity=2, speed_kmh=60.0,
              status=AmbulanceStatus.AVAILABLE),
    Hospital(id="H1", name="Central General", node_id="N8", total_beds=48,
             available_beds=12, total_icu=8, available_icu=2),
    Shelter(id="S1", name="Highland School", node_id="N20", capacity=400,
            occupancy=0, safety_score=0.92),
    SensorReading(tick=90, sensor_id="SEN1", zone_id="Z1", rainfall_mm=18.4,
                  water_level_m=2.7, river_level_m=4.1,
                  observation=Observation.HIGH_WATER),
    Alert(id="AL1", tick=150, level=AlertLevel.CRITICAL, title="Road R17 blocked",
          message="Riverside corridor impassable.", source="simulation"),
    TimelineEntry(id="TL1", tick=150, category="ROAD", headline="ROAD R17 BLOCKED",
                  detail="Flood depth exceeded threshold.", ai_components=["BN"]),
    SimEvent(tick=150, type="ROAD_BLOCKED", payload={"road_id": "R17"}),
    SSEEnvelope(seq=1042, tick=150, type="road_status",
                payload={"road_id": "R17", "status": "BLOCKED"}),
    RouteResult(found=True, path=["N1", "N4", "N9"], edges=["R2", "R8"],
                total_cost=11.3, total_distance=9.1, nodes_generated=21,
                nodes_expanded=14, execution_ms=0.83,
                expansion_order=["N1", "N4", "N9"], environment_version=3),
    CSPResult(status="SOLVED",
              assignments={"E7": CSPAssignment(ambulance_id="A3", hospital_id="H1")},
              constraints_checked=46, conflicts=2, backtracks=1,
              domain_reductions=6, execution_ms=1.4),
    HMMResult(belief={FloodState.NORMAL: 0.03, FloodState.RISING: 0.08,
                      FloodState.HIGH: 0.21, FloodState.CRITICAL: 0.68},
              most_likely=FloodState.CRITICAL,
              observation_history=[Observation.HIGH_WATER],
              belief_history=[[0.03, 0.08, 0.21, 0.68]], execution_ms=0.2),
    BayesResult(query="P(RoadFailure=TRUE | R17)", probability=0.71,
                evidence={"Rainfall": "HIGH", "WaterLevel": "HIGH"},
                per_road={"R17": 0.71}, execution_ms=0.4),
    InferenceResult(initial_facts=["WaterLevelHigh(Z1)"],
                    derived_facts=["Unsafe(R17)"], iterations=3, execution_ms=0.1),
    PlanResult(status="FOUND", goal="Resolved(E7)", plan_length=8, nodes_expanded=23,
               execution_ms=2.1,
               hierarchy=PlanNode(task="HandleEmergency(E7)", method="standard",
                                  children=[PlanNode(task="Respond(E7)",
                                                     primitive=False)])),
]


@pytest.mark.parametrize("model", SAMPLES, ids=lambda m: type(m).__name__)
def test_model_round_trips_through_json(model):
    _round_trip(model)


def test_road_status_is_derived_not_stored():
    road = Road(id="R1", source="N1", destination="N2", distance=3.0,
                geometric_length=3.0, detour_factor=1.0,
                elevation_band=ElevationBand.MED)
    assert road.status is RoadStatus.SAFE
    assert "status" not in road.model_dump()

    road.failure_probability = 0.5
    assert road.status is RoadStatus.RISKY

    road.blocked = True
    assert road.status is RoadStatus.BLOCKED


def test_road_base_cost_equals_distance():
    road = Road(id="R1", source="N1", destination="N2", distance=3.7,
                geometric_length=3.0, detour_factor=1.2333,
                elevation_band=ElevationBand.MED)
    assert road.base_cost == road.distance


def test_road_violating_invariant_w1_is_rejected():
    """distance < geometric_length would break A* admissibility."""
    with pytest.raises(ValueError, match="violates world invariant W1"):
        Road(id="RBAD", source="N1", destination="N2", distance=2.0,
             geometric_length=3.0, detour_factor=1.0,
             elevation_band=ElevationBand.LOW)


def test_hospital_rejects_more_available_than_total_beds():
    with pytest.raises(ValueError, match="exceeds total_beds"):
        Hospital(id="H9", name="Bad", node_id="N1", total_beds=10,
                 available_beds=11, total_icu=2, available_icu=0)


def test_hospital_status_transitions_with_capacity():
    hospital = Hospital(id="H1", name="Central", node_id="N1", total_beds=40,
                        available_beds=40, total_icu=8, available_icu=8)
    assert hospital.status.value == "OPEN"
    hospital.available_beds = 8
    assert hospital.status.value == "STRAINED"
    hospital.available_beds = 0
    assert hospital.status.value == "FULL"


def test_shelter_rejects_overfilled_occupancy():
    with pytest.raises(ValueError, match="exceeds capacity"):
        Shelter(id="S9", name="Bad", node_id="N1", capacity=10, occupancy=11,
                safety_score=0.5)
