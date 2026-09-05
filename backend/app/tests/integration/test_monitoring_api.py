"""Phase 11 monitoring API contract tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_monitoring_status_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/ai/monitoring/status")
    assert response.status_code == 200
    body = response.json()
    assert {"status", "tick", "overall", "health", "items", "alerts", "recommendations"}.issubset(body)


def test_replan_check_contract() -> None:
    with TestClient(app) as client:
        response = client.post("/api/ai/monitoring/replan-check")
    assert response.status_code == 200
    body = response.json()
    assert "plan_status" in body
    assert "plan_length" in body
