from fastapi.testclient import TestClient

from app.main import app
from app.simulation.engine import engine


def test_evidence_endpoint_returns_contract():
    with TestClient(app) as client:
        response = client.post("/api/ai/evidence", json={"max_sources": 4})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"FUSED", "NO_EVIDENCE"}
    assert body["frame"] == ["NORMAL", "RISING", "HIGH", "CRITICAL"]
    assert "combined_masses" in body
    assert "belief" in body
    assert "plausibility" in body
    assert "pignistic" in body
