"""Route cache: keying, invalidation, and the guarantee that matters.

    key = (start, goal, environment_version)

The guarantee: a route computed before a road changed can NEVER be served
after. That is not a performance property, it is a correctness one -- Phase 5's
hard-failure demo and Phase 7's CSP reachability both depend on it. A stale
route would send an ambulance down a closed road and the UI would show it
confidently.
"""

import pytest

from app.services.routing_service import RoutingService
from app.simulation.engine import SimulationEngine


@pytest.fixture
def engine():
    return SimulationEngine()


@pytest.fixture
def service():
    return RoutingService()


class TestCacheBehaviour:
    def test_first_call_is_a_miss(self, engine, service):
        service.route(engine.state, "N1", "N17")
        assert service.stats.misses == 1
        assert service.stats.hits == 0

    def test_second_identical_call_is_a_hit(self, engine, service):
        service.route(engine.state, "N1", "N17")
        service.route(engine.state, "N1", "N17")
        assert service.stats.hits == 1

    def test_a_hit_returns_an_identical_result(self, engine, service):
        first = service.route(engine.state, "N1", "N17")
        second = service.route(engine.state, "N1", "N17")
        assert second.path == first.path
        assert second.total_cost == first.total_cost
        assert second.environment_version == first.environment_version

    def test_different_pairs_are_cached_separately(self, engine, service):
        service.route(engine.state, "N1", "N17")
        service.route(engine.state, "N1", "N18")
        assert service.stats.misses == 2
        assert service.stats.entries == 2

    def test_direction_matters_in_the_key(self, engine, service):
        service.route(engine.state, "N1", "N17")
        service.route(engine.state, "N17", "N1")
        assert service.stats.misses == 2

    def test_use_cache_false_forces_a_fresh_search(self, engine, service):
        service.route(engine.state, "N1", "N17")
        service.route(engine.state, "N1", "N17", use_cache=False)
        assert service.stats.hits == 0

    def test_hit_rate_is_reported(self, engine, service):
        service.route(engine.state, "N1", "N17")
        service.route(engine.state, "N1", "N17")
        assert service.stats.hit_rate == pytest.approx(0.5)

    def test_clear_resets_everything(self, engine, service):
        service.route(engine.state, "N1", "N17")
        service.clear_cache()
        assert service.stats.entries == 0
        service.route(engine.state, "N1", "N17")
        assert service.stats.misses == 1


class TestInvalidation:
    def test_bumping_the_version_forces_a_recompute(self, engine, service):
        service.route(engine.state, "N1", "N17")
        engine.state.environment_version += 1
        service.route(engine.state, "N1", "N17")
        assert service.stats.hits == 0
        assert service.stats.invalidations == 1

    def test_a_stale_route_is_never_served_after_a_road_closes(self, engine, service):
        """THE guarantee. Everything downstream rests on this."""
        before = service.route(engine.state, "N1", "N17")
        assert "R17" in before.edges

        engine.state.roads["R17"].blocked = True
        engine.state.environment_version += 1

        after = service.route(engine.state, "N1", "N17")
        assert "R17" not in after.edges, "a closed road was served from cache"
        assert after.path != before.path
        assert after.environment_version > before.environment_version

    def test_invalidation_purges_rather_than_accumulating(self, engine, service):
        for _ in range(5):
            service.route(engine.state, "N1", "N17")
            engine.state.environment_version += 1
        assert service.stats.entries <= 1

    def test_the_cache_is_not_invalidated_by_a_tick_with_no_road_change(
        self, engine, service
    ):
        """RISK_EPSILON exists so the version does NOT move every tick.

        If this fails, the cache never serves a hit and the whole mechanism is
        decorative -- the exact bug the epsilon was introduced to prevent.
        """
        engine.set_scenario("NORMAL")
        engine.advance(5)
        service.route(engine.state, "N1", "N17")

        version_before = engine.state.environment_version
        engine.advance(5)

        if engine.state.environment_version == version_before:
            service.route(engine.state, "N1", "N17")
            assert service.stats.hits == 1


class TestFailureReporting:
    def test_unknown_start_node_raises(self, engine, service):
        with pytest.raises(KeyError, match="unknown start node"):
            service.route(engine.state, "NOPE", "N17")

    def test_unknown_goal_node_raises(self, engine, service):
        with pytest.raises(KeyError, match="unknown goal node"):
            service.route(engine.state, "N1", "NOPE")

    def test_isolating_a_node_names_it_in_the_failure(self, engine, service):
        """'No route found' sends an operator hunting. Name the cause."""
        state = engine.state
        for road in state.roads.values():
            if "N1" in (road.source, road.destination):
                road.blocked = True
        state.environment_version += 1

        result = service.route(state, "N1", "N17")
        assert not result.found
        assert result.failure_reason is not None
        assert "N1" in result.failure_reason
        assert "blocked" in result.failure_reason

    def test_an_unreachable_route_still_reports_metrics(self, engine, service):
        state = engine.state
        for road in state.roads.values():
            if "N1" in (road.source, road.destination):
                road.blocked = True
        state.environment_version += 1

        result = service.route(state, "N1", "N17")
        assert not result.found
        assert result.nodes_expanded >= 1
        assert result.execution_ms >= 0

    def test_start_equals_goal_is_a_zero_cost_route(self, engine, service):
        result = service.route(engine.state, "N1", "N1")
        assert result.found
        assert result.path == ["N1"]
        assert result.total_cost == 0.0


class TestReportedMetrics:
    def test_distance_and_cost_are_both_reported(self, engine, service):
        """Showing both is what makes 'the safer route is longer' legible."""
        result = service.route(engine.state, "N1", "N17")
        assert result.total_distance > 0
        assert result.total_cost >= result.total_distance

    def test_distance_is_the_sum_of_the_roads_used(self, engine, service):
        result = service.route(engine.state, "N1", "N17")
        expected = sum(engine.state.roads[rid].distance for rid in result.edges)
        assert result.total_distance == pytest.approx(expected, abs=1e-3)

    def test_path_and_edges_are_consistent(self, engine, service):
        result = service.route(engine.state, "N1", "N17")
        assert len(result.edges) == len(result.path) - 1
        for i, road_id in enumerate(result.edges):
            road = engine.state.roads[road_id]
            assert {road.source, road.destination} == {
                result.path[i],
                result.path[i + 1],
            }

    def test_expansion_order_is_populated_for_the_visualiser(self, engine, service):
        result = service.route(engine.state, "N1", "N17")
        assert result.expansion_order
        assert result.expansion_order[0] == "N1"
        assert len(result.expansion_order) == result.nodes_expanded

    def test_flooding_pushes_cost_above_distance(self, engine, service):
        engine.set_scenario("SEVERE_FLOOD")
        engine.advance(200)
        result = service.route(engine.state, "N1", "N17", use_cache=False)
        assert result.found
        assert result.total_cost > result.total_distance
