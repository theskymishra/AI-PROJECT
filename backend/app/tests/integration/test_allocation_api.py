import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.routing_service import routing_service
from app.simulation.engine import engine


@pytest.fixture
def client():
    engine.reset()
    routing_service.clear_cache()
    client = TestClient(create_app())
    client.post("/api/simulation/scenario", json={"name": "SEVERE_FLOOD"})
    client.post("/api/simulation/advance", json={"ticks": 180})
    return client


def test_allocation_preview_returns_csp_metrics(client):
    response = client.post("/api/ai/allocate", json={"apply": False})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"SOLVED", "PARTIAL", "UNSATISFIABLE"}
    assert body["constraints_checked"] > 0
    assert body["execution_ms"] >= 0
    assert isinstance(body["trace"], list)


def test_allocation_apply_commits_assignments_when_available(client):
    response = client.post("/api/ai/allocate", json={"apply": True})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"SOLVED", "PARTIAL", "UNSATISFIABLE"}
    if body["assignments"]:
        snapshot = client.get("/api/simulation/state").json()
        by_id = {e["id"]: e for e in snapshot["emergencies"]}
        for emergency_id, assignment in body["assignments"].items():
            assert by_id[emergency_id]["assigned_ambulance"] == assignment["ambulance_id"]
            assert by_id[emergency_id]["assigned_hospital"] == assignment["hospital_id"]
