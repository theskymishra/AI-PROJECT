import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.simulation.engine import engine
from app.services.routing_service import routing_service


@pytest.fixture
def client():
    engine.reset()
    routing_service.clear_cache()
    client = TestClient(create_app())
    client.post("/api/simulation/scenario", json={"name": "SEVERE_FLOOD"})
    client.post("/api/simulation/advance", json={"ticks": 145})
    return client

def test_inference_endpoint_exposes_live_knowledge(client):
    response = client.post("/api/ai/infer", json={})
    assert response.status_code == 200
    body = response.json()
    assert "HighFailureProb(R17)" in body["initial_facts"]
    assert "Unsafe(R17)" in body["derived_facts"]
    assert "Avoid(R17)" in body["derived_facts"]
    assert body["steps"]
    assert body["iterations"] >= 1


def test_fol_endpoint_returns_risky_road_bindings(client):
    response = client.post("/api/ai/fol", json={"query": "Unsafe(R) & Road(R)"})
    assert response.status_code == 200
    body = response.json()
    ids = {row["R"] for row in body["bindings"]}
    assert "R17" in ids
    assert body["count"] == len(ids)


def test_fol_rejects_invalid_query(client):
    response = client.post("/api/ai/fol", json={"query": "not a predicate"})
    assert response.status_code == 422
