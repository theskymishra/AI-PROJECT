"""End-to-end API behaviour for the simulation core."""

import pytest
import json
import time

from fastapi.testclient import TestClient

from app.main import create_app
from app.simulation.engine import engine


@pytest.fixture(autouse=True)
def fresh_engine():
    """Reset the process-wide engine around every test.

    A module-level singleton is the right shape for an in-memory single-worker
    simulation, but it makes tests order-dependent unless reset explicitly.
    """
    engine.reset("SEVERE_FLOOD")
    yield
    engine.reset("SEVERE_FLOOD")


@pytest.fixture
def client():
    return TestClient(create_app())


# -- snapshot --------------------------------------------------------------


def test_state_returns_a_complete_snapshot(client):
    body = client.get("/api/simulation/state").json()
    for key in (
        "clock", "scenario", "environment", "stats", "nodes", "zones", "roads",
        "emergencies", "ambulances", "hospitals", "shelters", "sensors",
        "timeline", "alerts",
    ):
        assert key in body, f"snapshot missing {key}"
    assert len(body["nodes"]) == 24
    assert len(body["roads"]) == 38
    assert len(body["hospitals"]) == 3


def test_snapshot_includes_derived_status_fields(client):
    body = client.get("/api/simulation/state").json()
    assert body["roads"][0]["status"] in {"SAFE", "RISKY", "BLOCKED"}
    assert body["hospitals"][0]["status"] in {"OPEN", "STRAINED", "FULL"}


def test_fresh_simulation_is_idle_at_tick_zero(client):
    clock = client.get("/api/simulation/state").json()["clock"]
    assert clock["tick"] == 0
    assert clock["status"] == "IDLE"
    assert clock["elapsed_label"] == "00:00"


# -- control ---------------------------------------------------------------


def test_start_pause_resume_transitions(client):
    assert client.post("/api/simulation/start").json()["clock"]["status"] == "RUNNING"
    assert client.post("/api/simulation/pause").json()["clock"]["status"] == "PAUSED"
    assert client.post("/api/simulation/resume").json()["clock"]["status"] == "RUNNING"


def test_advance_steps_exactly_the_requested_ticks(client):
    body = client.post("/api/simulation/advance", json={"ticks": 42}).json()
    assert body["clock"]["tick"] == 42
    assert body["clock"]["elapsed_label"] == "00:42"


def test_reset_returns_to_tick_zero(client):
    client.post("/api/simulation/advance", json={"ticks": 100})
    assert client.post("/api/simulation/reset").json()["clock"]["tick"] == 0


@pytest.mark.parametrize("speed", [1, 2, 5])
def test_supported_speeds_are_accepted(client, speed):
    assert client.post("/api/simulation/speed", json={"speed": speed}).json()[
        "clock"
    ]["speed"] == speed


@pytest.mark.parametrize("speed", [0, 3, 7, -1])
def test_unsupported_speeds_are_rejected(client, speed):
    assert client.post("/api/simulation/speed", json={"speed": speed}).status_code == 422


def test_advance_rejects_zero_and_negative(client):
    assert client.post("/api/simulation/advance", json={"ticks": 0}).status_code == 422
    assert client.post("/api/simulation/advance", json={"ticks": -5}).status_code == 422


# -- scenarios -------------------------------------------------------------


def test_scenarios_are_listed(client):
    names = {s["name"] for s in client.get("/api/simulation/scenarios").json()}
    assert names == {"NORMAL", "MODERATE_FLOOD", "SEVERE_FLOOD", "DYNAMIC_ROAD_FAILURE"}


def test_switching_scenario_resets_the_clock(client):
    client.post("/api/simulation/advance", json={"ticks": 50})
    body = client.post("/api/simulation/scenario", json={"name": "NORMAL"}).json()
    assert body["scenario"]["name"] == "NORMAL"
    assert body["clock"]["tick"] == 0


def test_unknown_scenario_is_a_404(client):
    assert client.post(
        "/api/simulation/scenario", json={"name": "APOCALYPSE"}
    ).status_code == 404


# -- the SEVERE_FLOOD script -----------------------------------------------


def test_bridge_closes_at_tick_150(client):
    before = client.post("/api/simulation/advance", json={"ticks": 149}).json()
    assert next(r for r in before["roads"] if r["id"] == "R17")["blocked"] is False

    after = client.post("/api/simulation/advance", json={"ticks": 1}).json()
    r17 = next(r for r in after["roads"] if r["id"] == "R17")
    assert r17["blocked"] is True
    assert r17["status"] == "BLOCKED"
    assert after["stats"]["blocked_roads"] == 1


def test_blocking_the_bridge_bumps_environment_version(client):
    before = client.post("/api/simulation/advance", json={"ticks": 149}).json()
    after = client.post("/api/simulation/advance", json={"ticks": 1}).json()
    assert (
        after["environment"]["environment_version"]
        > before["environment"]["environment_version"]
    )


def test_environment_version_grows_slowly_not_once_per_tick(client):
    """The Phase 0 correction, observed end to end."""
    body = client.post("/api/simulation/advance", json={"ticks": 300}).json()
    version = body["environment"]["environment_version"]
    assert version < 60, f"{version} invalidations in 300 ticks defeats the cache"
    assert version > 0, "nothing invalidated at all in a severe flood"


def test_emergency_e7_appears_at_tick_180_with_derived_patients(client):
    body = client.post("/api/simulation/advance", json={"ticks": 180}).json()
    e7 = next(e for e in body["emergencies"] if e["id"] == "E7")
    assert e7["severity"] == "CRITICAL"
    assert e7["people_affected"] == 9
    assert e7["patients"] == 3          # 1 + 5 // 2
    assert e7["node_id"] == "N1"
    assert e7["zone_id"] == "Z1"


def test_hidden_flood_state_escalates_over_the_run(client):
    early = client.post("/api/simulation/advance", json={"ticks": 20}).json()
    late = client.post("/api/simulation/advance", json={"ticks": 280}).json()
    assert early["environment"]["true_flood_state"] == "NORMAL"
    assert late["environment"]["true_flood_state"] in {"HIGH", "CRITICAL"}


def test_timeline_records_the_scripted_events(client):
    body = client.post("/api/simulation/advance", json={"ticks": 320}).json()
    headlines = [t["headline"] for t in body["timeline"]]
    assert "ROAD R17 BLOCKED" in headlines
    assert "EMERGENCY E7 REPORTED" in headlines
    assert any(h.startswith("WATER LEVEL") for h in headlines)


def test_run_completes_at_the_scenario_duration(client):
    body = client.post("/api/simulation/advance", json={"ticks": 520}).json()
    assert body["clock"]["status"] == "COMPLETED"


# -- manual controls -------------------------------------------------------


def test_operator_can_block_and_restore_a_road(client):
    assert client.post("/api/disaster/road/block", json={"road_id": "R25"}).status_code == 200
    roads = client.get("/api/simulation/state").json()["roads"]
    assert next(r for r in roads if r["id"] == "R25")["blocked"] is True

    client.post("/api/disaster/road/restore", json={"road_id": "R25"})
    roads = client.get("/api/simulation/state").json()["roads"]
    assert next(r for r in roads if r["id"] == "R25")["blocked"] is False


def test_double_blocking_returns_409_not_a_crash(client):
    client.post("/api/disaster/road/block", json={"road_id": "R25"})
    assert client.post(
        "/api/disaster/road/block", json={"road_id": "R25"}
    ).status_code == 409


def test_blocking_an_unknown_road_returns_409(client):
    assert client.post(
        "/api/disaster/road/block", json={"road_id": "R999"}
    ).status_code == 409


def test_manual_events_reach_the_timeline_like_scripted_ones(client):
    client.post("/api/disaster/road/block", json={"road_id": "R25"})
    timeline = client.get("/api/simulation/state").json()["timeline"]
    assert timeline[-1]["headline"] == "ROAD R25 BLOCKED"


def test_environment_nudge_requires_at_least_one_field(client):
    assert client.post("/api/disaster/update", json={}).status_code == 422


def test_environment_nudge_moves_the_target(client):
    before = client.get("/api/simulation/state").json()["environment"]
    client.post("/api/disaster/update", json={"water_level_delta_m": 1.5})
    client.post("/api/simulation/advance", json={"ticks": 100})
    after = client.get("/api/simulation/state").json()["environment"]
    assert after["water_level_m"] > before["water_level_m"]


def test_hospital_overload_endpoint(client):
    client.post(
        "/api/disaster/hospital/overload",
        json={"hospital_id": "H2", "available_beds": 0, "available_icu": 0},
    )
    hospitals = client.get("/api/simulation/state").json()["hospitals"]
    assert next(h for h in hospitals if h["id"] == "H2")["status"] == "FULL"


# -- emergencies and resources ---------------------------------------------


def test_creating_an_emergency_derives_patients(client):
    body = client.post(
        "/api/emergencies",
        json={
            "node_id": "N4", "severity": "HIGH",
            "people_affected": 12, "medical_priority": 4,
        },
    ).json()
    assert body["patients"] == 3
    assert body["people_affected"] == 12


def test_patients_cannot_be_supplied_by_the_caller(client):
    """The rule has one definition; the API must not let it be bypassed."""
    response = client.post(
        "/api/emergencies",
        json={
            "node_id": "N4", "severity": "LOW", "people_affected": 10,
            "medical_priority": 1, "patients": 4,
        },
    )
    assert response.json()["patients"] == 1     # 1 + 1 // 2, not the supplied 4


def test_emergency_at_an_unknown_node_returns_409(client):
    assert client.post(
        "/api/emergencies",
        json={"node_id": "N999", "severity": "LOW",
              "people_affected": 1, "medical_priority": 1},
    ).status_code == 409


def test_missing_emergency_returns_404(client):
    assert client.get("/api/emergencies/NOPE").status_code == 404


def test_resource_endpoints(client):
    assert len(client.get("/api/ambulances").json()) == 4
    assert len(client.get("/api/hospitals").json()) == 3
    assert len(client.get("/api/shelters").json()) == 2


def test_ambulance_capacities_match_the_fleet_spec(client):
    capacities = sorted(a["capacity"] for a in client.get("/api/ambulances").json())
    assert capacities == [2, 2, 4, 4]


# -- stream ----------------------------------------------------------------


def test_stream_reports_health(client):
    body = client.get("/api/simulation/stream-health").json()
    assert body["subscribers"] == 0
    assert body["dropped_frames"] == 0


# The SSE endpoint itself is NOT tested through TestClient.
#
# /api/stream is an infinite generator. Starlette's TestClient drives the app
# through a portal thread, and closing a streaming response waits on the
# response task while the response task waits on the subscriber queue --
# neither side moves and the suite hangs rather than fails. A hung CI job is
# worse than a red one, so the endpoint is verified two ways instead:
#
#   1. app/tests/unit/test_broadcast.py exercises the fan-out, backpressure
#      and unsubscribe logic in process, with no HTTP at all.
#   2. scripts/verify_sse.sh drives the real endpoint with curl against a real
#      uvicorn process, which is what a browser actually does.
#
# What is asserted here is only that the route is mounted.


def test_stream_route_is_registered(client):
    schema = client.get("/openapi.json").json()
    assert "/api/stream" in schema["paths"]
