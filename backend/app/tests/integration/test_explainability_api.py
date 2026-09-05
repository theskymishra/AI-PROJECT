"""Phase 12 explainability API contract tests."""
from fastapi.testclient import TestClient

from app.main import app
from app.simulation.engine import engine


def test_explainability_endpoint_returns_contract() -> None:
    engine.reset("NORMAL")
    response = TestClient(app).get("/api/ai/explainability/report")
    assert response.status_code == 200
    payload = response.json()
    assert {"status", "tick", "summary", "ai_chain", "explanations", "audit_events", "plan_status", "plan_length"} <= payload.keys()
