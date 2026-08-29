"""POST /api/ai/route against live simulation state.

Exercises the same RoutingService the simulation uses -- not a parallel demo
path -- so a passing test here means the endpoint an examiner pokes at is the
real thing.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.routing_service import routing_service
from app.simulation.engine import engine


@pytest.fixture
def client():
    engine.reset()
    routing_service.clear_cache()
    return TestClient(create_app())


def route(client, start="N1", goal="N17", **kwargs):
    body = {"start": start, "goal": goal, **kwargs}
    return client.post("/api/ai/route", json=body)


class TestHappyPath:
    def test_returns_200_and_a_route(self, client):
        response = route(client)
        assert response.status_code == 200
        assert response.json()["route"]["found"] is True

    def test_response_carries_the_full_RouteResult_contract(self, client):
        body = route(client).json()["route"]
        for field in (
            "found", "path", "edges", "total_cost", "total_distance",
            "nodes_generated", "nodes_expanded", "execution_ms",
            "expansion_order", "environment_version", "failure_reason",
        ):
            assert field in body, f"missing {field}"

    def test_metrics_are_real_not_placeholders(self, client):
        body = route(client).json()["route"]
        assert body["nodes_expanded"] > 1
        assert body["nodes_generated"] >= body["nodes_expanded"]
        assert body["execution_ms"] >= 0
        assert len(body["expansion_order"]) == body["nodes_expanded"]

    def test_path_starts_at_the_start_and_ends_at_the_goal(self, client):
        body = route(client, "N1", "N18").json()["route"]
        assert body["path"][0] == "N1"
        assert body["path"][-1] == "N18"

    def test_cost_weights_are_exposed(self, client):
        weights = route(client).json()["weights"]
        assert weights["flood"] == 2.0
        assert weights["damage"] == 1.5
        assert weights["failure"] == 3.0

    def test_cache_statistics_are_exposed(self, client):
        route(client)
        cache = route(client).json()["cache"]
        assert cache["hits"] == 1
        assert cache["misses"] == 1
        assert cache["hit_rate"] == 0.5


class TestErrorHandling:
    def test_unknown_start_is_a_404_not_a_500(self, client):
        response = route(client, start="NOPE")
        assert response.status_code == 404
        assert "NOPE" in response.json()["detail"]

    def test_unknown_goal_is_a_404(self, client):
        assert route(client, goal="NOPE").status_code == 404

    def test_missing_fields_are_a_422(self, client):
        assert client.post("/api/ai/route", json={"start": "N1"}).status_code == 422

    def test_no_route_is_a_200_with_found_false(self, client):
        """An unreachable goal is a normal outcome, not an HTTP error."""
        for road in engine.state.roads.values():
            if "N1" in (road.source, road.destination):
                road.blocked = True
        engine.state.environment_version += 1

        response = route(client)
        assert response.status_code == 200
        body = response.json()["route"]
        assert body["found"] is False
        assert body["failure_reason"]
        assert body["path"] == []


class TestLiveIntegration:
    def test_blocking_a_road_through_the_disaster_api_changes_the_route(self, client):
        """The Phase 5 hard-failure demo, end to end through HTTP."""
        before = route(client).json()["route"]
        assert "R17" in before["edges"]

        blocked = client.post("/api/disaster/road/block", json={"road_id": "R17"})
        assert blocked.status_code == 200

        after = route(client).json()["route"]
        assert after["found"] is True
        assert "R17" not in after["edges"]
        assert after["path"] != before["path"]
        assert after["environment_version"] > before["environment_version"]
        assert after["total_cost"] > before["total_cost"]

    def test_advancing_the_simulation_raises_route_cost(self, client):
        """Flooding is disaster-aware routing's live input in Phase 4."""
        dry = route(client, use_cache=False).json()["route"]

        client.post("/api/simulation/scenario", json={"name": "SEVERE_FLOOD"})
        client.post("/api/simulation/advance", json={"ticks": 200})
        flooded = route(client, use_cache=False).json()["route"]

        assert flooded["total_cost"] > dry["total_cost"], (
            "flood levels must feed the cost function"
        )

    def test_route_is_reproducible_for_the_same_state(self, client):
        first = route(client, use_cache=False).json()["route"]
        second = route(client, use_cache=False).json()["route"]
        assert first["path"] == second["path"]
        assert first["expansion_order"] == second["expansion_order"]
        assert first["total_cost"] == second["total_cost"]

    def test_endpoint_is_registered_in_the_schema(self, client):
        schema = client.get("/openapi.json").json()
        assert "/api/ai/route" in schema["paths"]
