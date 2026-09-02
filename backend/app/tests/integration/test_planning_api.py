from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_plan_endpoint_returns_contract():
    client = TestClient(app)
    response = client.post("/api/ai/plan")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"FOUND", "NO_PLAN"}
    assert "goal" in body
    assert "actions" in body
    assert "hierarchy" in body
    assert "execution_ms" in body
