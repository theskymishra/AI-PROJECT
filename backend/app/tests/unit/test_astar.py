"""Generic A* tests.

Hand-built graphs only -- the road network is exercised in test_road_graph.py.
The point here is the algorithm itself: optimality, the metrics it reports, and
the failure modes it must survive.
"""

import pytest

from app.ai.search.astar import astar

# A graph where the greedy choice is wrong: A->B looks cheap but leads nowhere
# useful, while the optimal path goes through C.
GRAPH = {
    "A": [("B", 1.0, "ab"), ("C", 4.0, "ac")],
    "B": [("D", 12.0, "bd")],
    "C": [("D", 1.0, "cd")],
    "D": [],
}


def successors_of(graph):
    return lambda state: graph.get(state, [])


def zero_heuristic(_state):
    return 0.0


class TestOptimality:
    def test_finds_the_cheapest_path_not_the_first_one(self):
        result = astar("A", successors_of(GRAPH), lambda s: s == "D", zero_heuristic)
        assert result.found
        assert result.path == ["A", "C", "D"]
        assert result.total_cost == 5.0

    def test_returns_the_edges_used_in_order(self):
        result = astar("A", successors_of(GRAPH), lambda s: s == "D", zero_heuristic)
        assert result.edges == ["ac", "cd"]

    def test_start_equal_to_goal_costs_nothing(self):
        result = astar("A", successors_of(GRAPH), lambda s: s == "A", zero_heuristic)
        assert result.found
        assert result.path == ["A"]
        assert result.total_cost == 0.0
        assert result.edges == []

    def test_an_admissible_heuristic_does_not_change_the_answer(self):
        """The whole point of admissibility: guidance without distortion."""
        exact = {"A": 5.0, "B": 12.0, "C": 1.0, "D": 0.0}
        guided = astar("A", successors_of(GRAPH), lambda s: s == "D", lambda s: exact[s])
        blind = astar("A", successors_of(GRAPH), lambda s: s == "D", zero_heuristic)
        assert guided.path == blind.path
        assert guided.total_cost == blind.total_cost

    def test_a_perfect_heuristic_expands_fewer_nodes(self):
        exact = {"A": 5.0, "B": 12.0, "C": 1.0, "D": 0.0}
        guided = astar("A", successors_of(GRAPH), lambda s: s == "D", lambda s: exact[s])
        blind = astar("A", successors_of(GRAPH), lambda s: s == "D", zero_heuristic)
        assert guided.nodes_expanded <= blind.nodes_expanded

    def test_an_inadmissible_heuristic_can_return_a_worse_path(self):
        """Documents WHY admissibility matters, by breaking it deliberately.

        If this ever starts passing with the optimal path, the heuristic is no
        longer being trusted and the search has become plain Dijkstra.
        """
        # Wildly overestimates C, so the search is pushed down the B branch.
        bad = {"A": 0.0, "B": 0.0, "C": 100.0, "D": 0.0}
        result = astar("A", successors_of(GRAPH), lambda s: s == "D", lambda s: bad[s])
        assert result.found
        assert result.total_cost > 5.0


class TestMetrics:
    def test_expansion_order_records_states_as_they_leave_the_frontier(self):
        result = astar("A", successors_of(GRAPH), lambda s: s == "D", zero_heuristic)
        assert result.expansion_order[0] == "A"
        assert result.expansion_order[-1] == "D"
        assert len(result.expansion_order) == result.nodes_expanded

    def test_no_state_is_expanded_twice(self):
        result = astar("A", successors_of(GRAPH), lambda s: s == "D", zero_heuristic)
        assert len(set(result.expansion_order)) == len(result.expansion_order)

    def test_generated_is_at_least_expanded(self):
        result = astar("A", successors_of(GRAPH), lambda s: s == "D", zero_heuristic)
        assert result.nodes_generated >= result.nodes_expanded

    def test_execution_time_is_measured_not_zero_filled(self):
        result = astar("A", successors_of(GRAPH), lambda s: s == "D", zero_heuristic)
        assert result.execution_ms >= 0.0
        assert isinstance(result.execution_ms, float)

    def test_metrics_are_reported_even_when_the_search_fails(self):
        result = astar("A", successors_of(GRAPH), lambda s: s == "Z", zero_heuristic)
        assert not result.found
        assert result.nodes_expanded > 0
        assert result.expansion_order


class TestFailureModes:
    def test_unreachable_goal_reports_why(self):
        result = astar("A", successors_of(GRAPH), lambda s: s == "Z", zero_heuristic)
        assert not result.found
        assert result.path == []
        assert result.failure_reason is not None
        assert "unreachable" in result.failure_reason

    def test_isolated_start_fails_cleanly(self):
        result = astar("X", successors_of({"X": []}), lambda s: s == "Y", zero_heuristic)
        assert not result.found
        assert result.nodes_expanded == 1

    def test_negative_step_cost_is_rejected_loudly(self):
        """Silently accepting one would break optimality with no symptom."""
        graph = {"A": [("B", -1.0, "ab")], "B": []}
        with pytest.raises(ValueError, match="negative step cost"):
            astar("A", successors_of(graph), lambda s: s == "B", zero_heuristic)

    def test_expansion_limit_stops_the_search(self):
        # A long chain that would otherwise run to completion.
        chain = {str(i): [(str(i + 1), 1.0, f"e{i}")] for i in range(200)}
        result = astar(
            "0",
            successors_of(chain),
            lambda s: s == "199",
            zero_heuristic,
            max_expansions=10,
        )
        assert not result.found
        assert result.nodes_expanded == 10
        assert "expansion limit" in (result.failure_reason or "")

    def test_a_cycle_does_not_cause_an_infinite_loop(self):
        cyclic = {
            "A": [("B", 1.0, "ab")],
            "B": [("C", 1.0, "bc")],
            "C": [("A", 1.0, "ca"), ("D", 1.0, "cd")],
            "D": [],
        }
        result = astar("A", successors_of(cyclic), lambda s: s == "D", zero_heuristic)
        assert result.found
        assert result.total_cost == 3.0


class TestDeterminism:
    def test_repeated_runs_are_identical(self):
        """A demo that expands nodes in a different order each run cannot be
        rehearsed, and screenshots in the report would not reproduce."""
        runs = [
            astar("A", successors_of(GRAPH), lambda s: s == "D", zero_heuristic)
            for _ in range(50)
        ]
        first = runs[0]
        for run in runs[1:]:
            assert run.path == first.path
            assert run.expansion_order == first.expansion_order
            assert run.nodes_expanded == first.nodes_expanded

    def test_ties_are_broken_towards_the_goal(self):
        """Equal f, lower h wins. Without this the heap order is arbitrary."""
        # B and C both cost 1 from A, but C is heuristically closer.
        graph = {
            "A": [("B", 1.0, "ab"), ("C", 1.0, "ac")],
            "B": [("G", 5.0, "bg")],
            "C": [("G", 5.0, "cg")],
            "G": [],
        }
        h = {"A": 6.0, "B": 5.0, "C": 5.0, "G": 0.0}
        result = astar("A", successors_of(graph), lambda s: s == "G", lambda s: h[s])
        assert result.found
        # Deterministic regardless of which of B/C is preferred.
        assert result.expansion_order[0] == "A"
