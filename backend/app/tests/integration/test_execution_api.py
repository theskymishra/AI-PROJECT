"""Phase 10 execution API contract tests."""
from fastapi.testclient import TestClient

from app.main import app
from app.simulation.engine import engine


def test_prepare_endpoint_returns_execution_contract() -> None:
    engine.reset("NORMAL")
    response = TestClient(app).post("/api/ai/execution/prepare")
    assert response.status_code == 200
    payload = response.json()
    assert {"status", "plan", "next_action_index", "executed_count", "total_actions", "tick", "snapshot"} <= payload.keys()
