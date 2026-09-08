from fastapi.testclient import TestClient

from app.main import app


def test_final_report_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/ai/final-report")
        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == 14
        assert data["total_phases"] == 14
        assert len(data["subsystems"]) == 14
        assert data["subsystems"][13]["phase"] == 14
