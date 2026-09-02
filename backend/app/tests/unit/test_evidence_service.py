from app.models.sensor import SensorReading
from app.services.evidence_service import (
    FRAME,
    EvidenceFusionService,
    belief_and_plausibility,
    combine_masses,
    mass_for_observation,
    pignistic,
)
from app.simulation.state import WorldState


def test_observation_keeps_ignorance_mass():
    masses = mass_for_observation("HIGH_WATER")
    assert masses["{HIGH,CRITICAL}"] == 0.68
    assert masses["THETA"] == 0.32
    assert abs(sum(masses.values()) - 1.0) < 1e-9


def test_dempster_combination_normalizes_non_conflicting_mass():
    combined, conflict = combine_masses(
        {"{NORMAL,RISING}": 0.7, "THETA": 0.3},
        {"{RISING,HIGH}": 0.8, "THETA": 0.2},
    )
    assert conflict == 0.0
    assert abs(sum(combined.values()) - 1.0) < 1e-9
    belief, plausibility = belief_and_plausibility(combined)
    assert all(0.0 <= belief[s] <= plausibility[s] <= 1.0 for s in FRAME)
    assert abs(sum(pignistic(combined).values()) - 1.0) < 1e-9

def test_dempster_combination_detects_conflicting_mass():
    combined, conflict = combine_masses(
        {"{NORMAL}": 0.7, "THETA": 0.3},
        {"{CRITICAL}": 0.8, "THETA": 0.2},
    )

    assert conflict > 0.0
    assert conflict < 1.0
    assert abs(sum(combined.values()) - 1.0) < 1e-9

def test_service_fuses_latest_sensor_readings_without_mutation():
    state = WorldState.create("MODERATE_FLOOD")
    state.add_sensor_reading(
        SensorReading(
            tick=10, sensor_id="S1", zone_id="Z1", rainfall_mm=20,
            water_level_m=1.2, river_level_m=1.5, observation="MEDIUM_WATER",
        )
    )
    state.add_sensor_reading(
        SensorReading(
            tick=10, sensor_id="S2", zone_id="Z2", rainfall_mm=25,
            water_level_m=1.4, river_level_m=1.7, observation="HIGH_WATER",
        )
    )
    before = dict(state.sensors)
    result = EvidenceFusionService().analyze(state)
    assert result.status == "FUSED"
    assert result.evidence_count == 2
    assert abs(sum(result.pignistic.values()) - 1.0) < 1e-9
    assert state.sensors == before


def test_no_sensor_evidence_reports_ignorance():
    state = WorldState.create("NORMAL")
    result = EvidenceFusionService().analyze(state)
    assert result.status == "NO_EVIDENCE"
    assert result.combined_masses == {"THETA": 1.0}
    assert all(result.belief[s] == 0.0 for s in FRAME)
    assert all(result.plausibility[s] == 1.0 for s in FRAME)
