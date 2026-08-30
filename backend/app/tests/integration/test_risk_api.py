"""POST /api/ai/hmm and /api/ai/bayesian against live simulation state."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.simulation.engine import engine


@pytest.fixture
def client():
    engine.reset()
    c = TestClient(create_app())
    c.post("/api/simulation/scenario", json={"name": "SEVERE_FLOOD"})
    c.post("/api/simulation/advance", json={"ticks": 160})
    return c


class TestHMMEndpoint:
    def test_live_belief_is_returned(self, client):
        body = client.post("/api/ai/hmm", json={}).json()
        assert body["live"] is True
        assert set(body["belief"]) == {"NORMAL", "RISING", "HIGH", "CRITICAL"}
        assert abs(sum(body["belief"].values()) - 1.0) < 1e-9

    def test_live_belief_reflects_the_flood(self, client):
        body = client.post("/api/ai/hmm", json={}).json()
        assert body["most_likely"] in {"RISING", "HIGH", "CRITICAL"}

    def test_belief_is_uncertain_not_collapsed(self, client):
        body = client.post("/api/ai/hmm", json={}).json()
        assert max(body["belief"].values()) < 0.99
        assert body["entropy"] > 0.1

    def test_history_is_returned_for_charting(self, client):
        body = client.post("/api/ai/hmm", json={}).json()
        assert len(body["observation_history"]) > 100
        assert len(body["belief_history"]) == len(body["observation_history"]) + 1
        assert all(len(row) == 4 for row in body["belief_history"])

    def test_a_supplied_sequence_runs_a_throwaway_filter(self, client):
        live_before = client.post("/api/ai/hmm", json={}).json()
        whatif = client.post(
            "/api/ai/hmm", json={"observations": ["LOW_WATER"] * 30}
        ).json()
        live_after = client.post("/api/ai/hmm", json={}).json()

        assert whatif["live"] is False
        assert whatif["most_likely"] == "NORMAL"
        assert live_after["belief"] == live_before["belief"], (
            "a what-if query disturbed the live filter"
        )

    def test_unknown_observation_is_a_422(self, client):
        response = client.post("/api/ai/hmm", json={"observations": ["TSUNAMI"]})
        assert response.status_code == 422


class TestBayesianEndpoint:
    def test_returns_a_probability_for_every_road(self, client):
        body = client.post("/api/ai/bayesian", json={}).json()
        assert len(body["per_road"]) == 38
        assert all(0.0 < p < 1.0 for p in body["per_road"].values())

    def test_evidence_is_read_from_live_sensors(self, client):
        body = client.post("/api/ai/bayesian", json={}).json()
        assert body["evidence"]["Rainfall"] in {"LOW", "MED", "HIGH"}
        assert body["evidence"]["WaterLevel"] in {"LOW", "MED", "HIGH"}

    def test_virtual_evidence_is_used_by_default(self, client):
        assert client.post("/api/ai/bayesian", json={}).json()[
            "used_hmm_virtual_evidence"
        ]

    def test_detaching_the_hmm_changes_the_posterior(self, client):
        """The what-if mode that makes the rainfall chain inspectable."""
        with_hmm = client.post("/api/ai/bayesian", json={}).json()
        without = client.post("/api/ai/bayesian", json={"use_hmm": False}).json()
        assert without["used_hmm_virtual_evidence"] is False
        assert with_hmm["flood_severity"] != without["flood_severity"], (
            "the HMM contributes nothing; virtual evidence is not wired"
        )

    def test_clamping_evidence_changes_the_result(self, client):
        calm = client.post(
            "/api/ai/bayesian",
            json={"rainfall": "LOW", "water_level": "LOW", "use_hmm": False},
        ).json()
        storm = client.post(
            "/api/ai/bayesian",
            json={"rainfall": "HIGH", "water_level": "HIGH", "use_hmm": False},
        ).json()
        assert storm["flood_severity"]["CRITICAL"] > calm["flood_severity"]["CRITICAL"]
        assert max(storm["per_road"].values()) > max(calm["per_road"].values())

    def test_riskiest_roads_are_ranked_and_low_lying(self, client):
        ranked = client.post("/api/ai/bayesian", json={}).json()["riskiest_roads"]
        assert len(ranked) == 5
        probabilities = [r["probability"] for r in ranked]
        assert probabilities == sorted(probabilities, reverse=True)
        assert ranked[0]["elevation_band"] == "LOW"

    def test_invalid_band_is_a_422(self, client):
        assert (
            client.post("/api/ai/bayesian", json={"rainfall": "NOPE"}).status_code == 422
        )

    def test_endpoints_are_registered(self, client):
        paths = client.get("/openapi.json").json()["paths"]
        assert "/api/ai/hmm" in paths
        assert "/api/ai/bayesian" in paths


class TestRiskReachesRouting:
    def test_road_failure_probabilities_match_the_live_roads(self, client):
        bayes = client.post("/api/ai/bayesian", json={}).json()["per_road"]
        roads = {r["id"]: r["failure_probability"] for r in
                 client.get("/api/simulation/state").json()["roads"]}
        for road_id, probability in bayes.items():
            assert abs(probability - roads[road_id]) < 0.02, (
                f"{road_id}: endpoint and world state disagree"
            )

    def test_route_cost_exceeds_distance_because_of_inferred_risk(self, client):
        body = client.post(
            "/api/ai/route", json={"start": "N1", "goal": "N17", "use_cache": False}
        ).json()["route"]
        assert body["total_cost"] > body["total_distance"]
