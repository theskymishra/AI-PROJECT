"""Health endpoint contract tests."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app

client = TestClient(create_app())


def test_health_returns_200():
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_payload_shape():
    body = client.get("/api/health").json()
    assert set(body) == {
        "status",
        "app",
        "full_name",
        "tagline",
        "version",
        "phase",
        "total_phases",
        "uptime_seconds",
    }


def test_health_reports_build_identity():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["app"] == settings.app_name
    assert body["version"] == settings.version
    assert body["phase"] == settings.phase


def test_uptime_is_non_negative_and_increases():
    first = client.get("/api/health").json()["uptime_seconds"]
    second = client.get("/api/health").json()["uptime_seconds"]
    assert first >= 0
    assert second >= first


def test_unknown_route_returns_404_not_a_crash():
    assert client.get("/api/does-not-exist").status_code == 404


def test_openapi_schema_is_generated():
    schema = client.get("/openapi.json").json()
    assert "/api/health" in schema["paths"]
