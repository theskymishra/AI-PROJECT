from fastapi.testclient import TestClient

from app.main import app


def test_evaluation_report_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/ai/evaluation/report")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "OK"
    assert "metrics" in payload
    assert "recommendations" in payload
