"""Road adapter tests: cost function, heuristic admissibility, and optimality.

THE ORACLE
----------
Proving A* returns the true optimum needs an independent ground truth, and the
obvious candidates -- BFS, DFS, uniform-cost, best-first -- are all on the
project's banned-algorithm list. Floyd-Warshall is used instead:

  * it is dynamic programming over an adjacency matrix, not a search, so it is
    not one of the banned techniques;
  * it lives ONLY in this test file, never in app/ai/, so it is not part of
    the demonstrated AI;
  * it computes all-pairs shortest costs in one pass, which lets every one of
    the 552 ordered node pairs be checked rather than a hand-picked few.

If A* disagrees with Floyd-Warshall on any pair, either the heuristic is
inadmissible or the search is wrong. Both are silent failures otherwise: a
suboptimal path still looks like a path.
"""

import functools
import math

import pytest

from app.ai.search.astar import astar
from app.ai.search.road_graph import (
    UNSAFE_PENALTY,
    RoadGraph,
    edge_cost,
    euclidean_km,
)
from app.config import (
    COST_WEIGHT_DAMAGE,
    COST_WEIGHT_FAILURE,
    COST_WEIGHT_FLOOD,
    SCALE_KM_PER_UNIT,
)
from app.models.common import ElevationBand
from app.models.road import Road
from app.simulation.engine import SimulationEngine
from app.simulation.world import build_world

WEIGHTS = {
    "alpha": COST_WEIGHT_FLOOD,
    "beta": COST_WEIGHT_DAMAGE,
    "gamma": COST_WEIGHT_FAILURE,
}


def make_road(**overrides) -> Road:
    base = {
        "id": "RT",
        "source": "N1",
        "destination": "N2",
        "distance": 10.0,
        "geometric_length": 9.0,
        "detour_factor": 1.111,
        "elevation_band": ElevationBand.MED,
    }
    return Road(**{**base, **overrides})


# ---------------------------------------------------------------------------
# Cost function
# ---------------------------------------------------------------------------


class TestEdgeCost:
    def test_a_pristine_road_costs_exactly_its_length(self):
        road = make_road()
        assert edge_cost(road, **WEIGHTS) == pytest.approx(10.0)

    def test_flooding_raises_the_cost_by_alpha_times_flood_level(self):
        road = make_road(flood_level=0.5)
        expected = 10.0 * (1 + COST_WEIGHT_FLOOD * 0.5)
        assert edge_cost(road, **WEIGHTS) == pytest.approx(expected)

    def test_damage_raises_the_cost_by_beta_times_damage_level(self):
        road = make_road(damage_level=0.4)
        expected = 10.0 * (1 + COST_WEIGHT_DAMAGE * 0.4)
        assert edge_cost(road, **WEIGHTS) == pytest.approx(expected)

    def test_failure_probability_raises_the_cost_by_gamma(self):
        """The Phase 5 term. Zero in live data today, so it is tested with an
        injected value -- otherwise the wiring would go unverified until the
        Bayesian Network lands and any bug would surface then."""
        road = make_road(failure_probability=1.0)
        expected = 10.0 * (1 + COST_WEIGHT_FAILURE)
        assert edge_cost(road, **WEIGHTS) == pytest.approx(expected)
        assert expected == pytest.approx(40.0)

    def test_the_three_terms_are_additive(self):
        road = make_road(flood_level=0.5, damage_level=0.4, failure_probability=0.2)
        expected = 10.0 * (
            1
            + COST_WEIGHT_FLOOD * 0.5
            + COST_WEIGHT_DAMAGE * 0.4
            + COST_WEIGHT_FAILURE * 0.2
        )
        assert edge_cost(road, **WEIGHTS) == pytest.approx(expected)

    def test_cost_is_never_below_the_road_length(self):
        """The inequality the admissibility proof rests on."""
        for flood in (0.0, 0.3, 1.0):
            for damage in (0.0, 0.5, 1.0):
                for pfail in (0.0, 0.7, 1.0):
                    road = make_road(
                        flood_level=flood,
                        damage_level=damage,
                        failure_probability=pfail,
                    )
                    assert edge_cost(road, **WEIGHTS) >= road.distance

    def test_negative_weights_are_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            RoadGraph(nodes={}, roads={}, alpha=-1.0, beta=0.0, gamma=0.0)


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


class TestRoadGraph:
    @pytest.fixture
    def world(self):
        return build_world()

    @pytest.fixture
    def graph(self, world):
        return RoadGraph(
            nodes=world.node_by_id, roads=dict(world.road_by_id), **WEIGHTS
        )

    def test_roads_are_bidirectional(self, graph, world):
        road = world.road_by_id["R17"]
        forward = [n for n, _, _ in graph.successors(road.source)]
        backward = [n for n, _, _ in graph.successors(road.destination)]
        assert road.destination in forward
        assert road.source in backward

    def test_every_node_has_at_least_two_neighbours(self, graph, world):
        """A degree-1 node is a dead end that adds nothing to a routing demo."""
        for node_id in world.node_by_id:
            assert graph.degree(node_id) >= 2, f"{node_id} is a dead end"

    def test_blocked_roads_are_not_traversable(self, world):
        roads = {rid: r.model_copy() for rid, r in world.road_by_id.items()}
        roads["R17"].blocked = True
        graph = RoadGraph(nodes=world.node_by_id, roads=roads, **WEIGHTS)
        edges = [e for _, _, e in graph.successors(roads["R17"].source)]
        assert "R17" not in edges

    def test_blocking_reduces_degree(self, world):
        roads = {rid: r.model_copy() for rid, r in world.road_by_id.items()}
        source = roads["R17"].source
        before = RoadGraph(nodes=world.node_by_id, roads=roads, **WEIGHTS).degree(source)
        roads["R17"].blocked = True
        after = RoadGraph(nodes=world.node_by_id, roads=roads, **WEIGHTS).degree(source)
        assert after == before - 1

    def test_avoided_roads_cost_more_but_stay_traversable(self, world):
        """Soft penalty from the knowledge engine, unlike the hard block."""
        roads = dict(world.road_by_id)
        plain = RoadGraph(nodes=world.node_by_id, roads=roads, **WEIGHTS)
        avoiding = RoadGraph(
            nodes=world.node_by_id, roads=roads, avoid=frozenset({"R17"}), **WEIGHTS
        )
        source = roads["R17"].source

        plain_cost = next(c for _, c, e in plain.successors(source) if e == "R17")
        avoid_cost = next(c for _, c, e in avoiding.successors(source) if e == "R17")

        assert avoid_cost == pytest.approx(plain_cost * UNSAFE_PENALTY)
        assert UNSAFE_PENALTY >= 1.0, "a penalty below 1 would break admissibility"


# ---------------------------------------------------------------------------
# Heuristic
# ---------------------------------------------------------------------------


class TestHeuristic:
    @pytest.fixture
    def world(self):
        return build_world()

    def test_heuristic_is_zero_at_the_goal(self, world):
        graph = RoadGraph(nodes=world.node_by_id, roads=dict(world.road_by_id), **WEIGHTS)
        assert graph.heuristic_to("N17")("N17") == 0.0

    def test_heuristic_is_straight_line_distance_in_kilometres(self, world):
        a = world.node_by_id["N1"]
        b = world.node_by_id["N17"]
        expected = SCALE_KM_PER_UNIT * math.hypot(a.x - b.x, a.y - b.y)
        assert euclidean_km(a, b) == pytest.approx(expected)

    def test_world_invariant_w1_holds_against_live_geometry(self, world):
        """distance >= SCALE * euclid(source, destination), computed exactly.

        This is the form of W1 the admissibility proof actually needs. The
        stored geometric_length field is rounded for display; the heuristic
        computes the straight line from node coordinates at query time, so
        that is what must be dominated. Testing the stored field instead
        would leave a rounding-sized hole in the proof.
        """
        for road in world.roads:
            a = world.node_by_id[road.source]
            b = world.node_by_id[road.destination]
            assert road.distance >= euclidean_km(a, b) - 1e-9, (
                f"{road.id} violates W1 ({road.distance} < {euclidean_km(a, b)}); "
                f"the A* heuristic is no longer admissible"
            )

    def test_stored_geometric_length_matches_the_coordinates(self, world):
        """The stored field is documentation, rounded to 4dp at build time."""
        for road in world.roads:
            a = world.node_by_id[road.source]
            b = world.node_by_id[road.destination]
            assert road.geometric_length == pytest.approx(
                euclidean_km(a, b), abs=1e-4
            )

    def test_heuristic_is_consistent_across_every_edge(self, world):
        """h(n) <= cost(n, n') + h(n') for all edges and all goals.

        Consistency is what makes the closed-set implementation correct. This
        checks all 38 roads x 24 goals in both directions.
        """
        graph = RoadGraph(nodes=world.node_by_id, roads=dict(world.road_by_id), **WEIGHTS)
        for goal_id in world.node_by_id:
            h = graph.heuristic_to(goal_id)
            for node_id in world.node_by_id:
                for neighbour, cost, _ in graph.successors(node_id):
                    assert h(node_id) <= cost + h(neighbour) + 1e-9, (
                        f"inconsistent at {node_id}->{neighbour} for goal {goal_id}"
                    )


# ---------------------------------------------------------------------------
# Optimality, against an independent oracle
# ---------------------------------------------------------------------------


def floyd_warshall(node_ids: list[str], graph: RoadGraph) -> dict[tuple[str, str], float]:
    """All-pairs cheapest costs. TEST ORACLE ONLY -- never used by the app.

    Dynamic programming over an adjacency matrix. Deliberately not any of the
    banned search algorithms, and deliberately not A*, so that agreement
    between the two is meaningful evidence rather than a tautology.
    """
    index = {node_id: i for i, node_id in enumerate(node_ids)}
    size = len(node_ids)
    dist = [[math.inf] * size for _ in range(size)]

    for i in range(size):
        dist[i][i] = 0.0
    for node_id in node_ids:
        for neighbour, cost, _ in graph.successors(node_id):
            i, j = index[node_id], index[neighbour]
            dist[i][j] = min(dist[i][j], cost)

    for k in range(size):
        for i in range(size):
            if dist[i][k] == math.inf:
                continue
            for j in range(size):
                candidate = dist[i][k] + dist[k][j]
                if candidate < dist[i][j]:
                    dist[i][j] = candidate

    return {
        (a, b): dist[index[a]][index[b]] for a in node_ids for b in node_ids
    }


@functools.lru_cache(maxsize=1)
def _oracle():
    """World, graph, node ids and all-pairs optimal costs. Computed once."""
    world = build_world()
    graph = RoadGraph(nodes=world.node_by_id, roads=dict(world.road_by_id), **WEIGHTS)
    node_ids = tuple(sorted(world.node_by_id))
    return world, graph, node_ids, floyd_warshall(list(node_ids), graph)


class TestOptimalityAgainstOracle:
    def test_astar_matches_the_oracle_on_every_ordered_pair(self):
        """All 24 x 23 = 552 ordered pairs. Not a spot check."""
        _world, graph, node_ids, optimal = _oracle()
        checked = 0
        for start in node_ids:
            for goal in node_ids:
                if start == goal:
                    continue
                result = astar(
                    start,
                    graph.successors,
                    lambda n, g=goal: n == g,
                    graph.heuristic_to(goal),
                )
                assert result.found, f"{start} -> {goal} unreachable in an open world"
                assert result.total_cost == pytest.approx(
                    optimal[(start, goal)], rel=1e-9
                ), f"A* is suboptimal for {start} -> {goal}"
                checked += 1
        assert checked == 552

    def test_the_heuristic_never_overestimates_on_any_pair(self):
        """Admissibility, measured rather than argued."""
        _world, graph, node_ids, optimal = _oracle()
        for goal in node_ids:
            h = graph.heuristic_to(goal)
            for start in node_ids:
                assert h(start) <= optimal[(start, goal)] + 1e-9, (
                    f"h({start} -> {goal}) = {h(start)} exceeds the true optimum "
                    f"{optimal[(start, goal)]}"
                )

    def test_the_heuristic_actually_helps(self):
        """An admissible heuristic that always returns 0 is also admissible.

        This proves the heuristic earns its place: guided search must expand
        strictly fewer nodes than blind search on a long route.
        """
        _world, graph, _node_ids, _optimal = _oracle()
        guided = astar("N1", graph.successors, lambda n: n == "N20", graph.heuristic_to("N20"))
        blind = astar("N1", graph.successors, lambda n: n == "N20", lambda _n: 0.0)
        assert guided.total_cost == pytest.approx(blind.total_cost)
        assert guided.nodes_expanded < blind.nodes_expanded


# ---------------------------------------------------------------------------
# Behaviour against live simulation state
# ---------------------------------------------------------------------------


class TestAgainstLiveState:
    def test_flooding_makes_routes_more_expensive_than_their_length(self):
        engine = SimulationEngine()
        engine.set_scenario("SEVERE_FLOOD")
        engine.advance(200)

        state = engine.state
        graph = RoadGraph(nodes=state.world.node_by_id, roads=state.roads, **WEIGHTS)
        result = astar(
            "N1", graph.successors, lambda n: n == "N17", graph.heuristic_to("N17")
        )
        assert result.found

        plain_km = sum(state.roads[str(e)].distance for e in result.edges)
        assert result.total_cost > plain_km, (
            "with the flood plain under water the risk-weighted cost must "
            "exceed the plain distance"
        )

    def test_blocking_the_bridge_changes_the_route(self):
        """R17 is the only direct Riverside-Midtown link by design."""
        engine = SimulationEngine()
        state = engine.state
        graph = RoadGraph(nodes=state.world.node_by_id, roads=state.roads, **WEIGHTS)
        before = astar(
            "N1", graph.successors, lambda n: n == "N17", graph.heuristic_to("N17")
        )
        assert "R17" in [str(e) for e in before.edges]

        state.roads["R17"].blocked = True
        blocked_graph = RoadGraph(
            nodes=state.world.node_by_id, roads=state.roads, **WEIGHTS
        )
        after = astar(
            "N1",
            blocked_graph.successors,
            lambda n: n == "N17",
            blocked_graph.heuristic_to("N17"),
        )

        assert after.found
        assert "R17" not in [str(e) for e in after.edges]
        assert after.path != before.path
        assert after.total_cost > before.total_cost, (
            "the detour must cost more, or R17 was not on the optimal route"
        )
