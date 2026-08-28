"""CORS configuration tests.

The frontend runs on a different origin from the backend during development, so
a CORS misconfiguration presents to the user as 'the dashboard shows offline'
with no obvious cause. These tests make that failure loud.
"""

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())

VITE_ORIGIN = "http://localhost:5173"


def test_allowed_origin_receives_cors_header():
    response = client.get("/api/health", headers={"Origin": VITE_ORIGIN})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == VITE_ORIGIN


def test_loopback_ip_origin_also_allowed():
    origin = "http://127.0.0.1:5173"
    response = client.get("/api/health", headers={"Origin": origin})
    assert response.headers["access-control-allow-origin"] == origin


def test_preflight_is_accepted():
    response = client.options(
        "/api/health",
        headers={
            "Origin": VITE_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == VITE_ORIGIN


def test_unlisted_origin_is_not_granted_access():
    response = client.get(
        "/api/health", headers={"Origin": "http://malicious.example.com"}
    )
    # The request itself still succeeds; the browser is what enforces CORS.
    # What matters is that no allow-origin header is granted.
    assert "access-control-allow-origin" not in response.headers
