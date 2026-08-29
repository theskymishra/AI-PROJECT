"""A* search, implemented from scratch.

    f(n) = g(n) + h(n)

GENERIC ON PURPOSE
------------------
This module knows nothing about roads. It takes a start state, a successor
function, a goal test and a heuristic, and it is used twice in this project:

    Phase 4   routing over the road network      (ai/search/road_graph.py)
    Phase 8   classical planning over STRIPS states (ai/planning/classical.py)

One search implementation serving both is not a cleverness for its own sake:
it means the expansion counts, the tie-breaking and the optimality argument
are identical in both places, so there is one thing to explain in a viva
rather than two.

OPTIMALITY
----------
A* returns an optimal solution when the heuristic is ADMISSIBLE (never
overestimates the true remaining cost). The closed-set implementation below --
which never re-opens an already-expanded state -- additionally requires the
heuristic to be CONSISTENT:

    h(n) <= cost(n, n') + h(n')     for every successor n' of n

The road heuristic satisfies both; the proofs are in road_graph.py, resting on
world invariant W1. If a future caller supplies an admissible-but-inconsistent
heuristic, this implementation may return a suboptimal path. That is a
deliberate trade (closed-set A* is far simpler to explain and to trace), and
it is stated here so the constraint is not discovered by accident.

TIE-BREAKING
------------
Equal-f states are ordered by lower h, then by insertion order. Preferring low
h breaks ties towards the goal, which measurably reduces expansions; the
insertion counter makes the ordering total, so a run is reproducible rather
than depending on how the heap happens to compare two payloads.
"""

from __future__ import annotations

import heapq
import time
from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

S = TypeVar("S", bound=Hashable)

#: (successor_state, step_cost, edge_reference)
#: edge_reference is opaque to the search -- roads pass a road id, the planner
#: passes an action -- and is threaded back out in the reconstructed path.
Successor = tuple[S, float, object]


@dataclass
class SearchResult(Generic[S]):
    """Outcome of one search, including the metrics the UI displays.

    Every metric here is counted by the algorithm as it runs. None of it may
    be estimated, and none of it may be filled in afterwards.
    """

    found: bool
    path: list[S] = field(default_factory=list)
    edges: list[object] = field(default_factory=list)
    total_cost: float = 0.0
    nodes_generated: int = 0
    nodes_expanded: int = 0
    execution_ms: float = 0.0
    #: States in the order they left the frontier. Drives the animation.
    expansion_order: list[S] = field(default_factory=list)
    failure_reason: str | None = None


def astar(
    start: S,
    successors: Callable[[S], Iterable[Successor[S]]],
    goal_test: Callable[[S], bool],
    heuristic: Callable[[S], float],
    *,
    max_expansions: int | None = None,
) -> SearchResult[S]:
    """Search from ``start`` to any state satisfying ``goal_test``.

    Args:
        start: Initial state.
        successors: Yields (state, step_cost, edge_ref) triples. Step costs
            must be non-negative; a negative cost breaks the optimality
            argument and raises.
        goal_test: True for a goal state.
        heuristic: Estimated remaining cost. Must be admissible and
            consistent for the result to be optimal.
        max_expansions: Safety valve. ``None`` means unbounded, which is
            correct for a finite graph; the planner passes a bound because its
            state space is not obviously finite.

    Returns:
        A SearchResult. ``found`` is False for an unreachable goal; that is a
        normal outcome (every road out of a zone can be blocked), not an error.
    """
    started_at = time.perf_counter()

    def finish(result: SearchResult[S]) -> SearchResult[S]:
        result.execution_ms = round((time.perf_counter() - started_at) * 1000, 4)
        return result

    # g[s] is the cheapest cost found so far from start to s.
    g: dict[S, float] = {start: 0.0}
    # parent[s] = (predecessor, edge used to reach s)
    parent: dict[S, tuple[S, object]] = {}
    closed: set[S] = set()

    counter = 0  # insertion order, for a total ordering on the heap
    frontier: list[tuple[float, float, int, S]] = [
        (heuristic(start), heuristic(start), counter, start)
    ]

    nodes_generated = 1  # the start state counts as generated
    nodes_expanded = 0
    expansion_order: list[S] = []

    while frontier:
        f, _h, _order, state = heapq.heappop(frontier)

        # Stale heap entry: this state was already expanded via a cheaper
        # route. Skipping is what makes the "decrease-key by re-push" trick
        # correct without a priority queue that supports decrease-key.
        if state in closed:
            continue

        closed.add(state)
        nodes_expanded += 1
        expansion_order.append(state)

        if goal_test(state):
            path, edges = _reconstruct(state, parent)
            return finish(
                SearchResult(
                    found=True,
                    path=path,
                    edges=edges,
                    total_cost=g[state],
                    nodes_generated=nodes_generated,
                    nodes_expanded=nodes_expanded,
                    expansion_order=expansion_order,
                )
            )

        if max_expansions is not None and nodes_expanded >= max_expansions:
            return finish(
                SearchResult(
                    found=False,
                    nodes_generated=nodes_generated,
                    nodes_expanded=nodes_expanded,
                    expansion_order=expansion_order,
                    failure_reason=(
                        f"expansion limit reached ({max_expansions}); "
                        f"no solution found within the budget"
                    ),
                )
            )

        for successor, step_cost, edge_ref in successors(state):
            if step_cost < 0:
                raise ValueError(
                    f"negative step cost {step_cost} from {state!r} to "
                    f"{successor!r}; A* optimality assumes non-negative costs"
                )
            if successor in closed:
                continue

            tentative = g[state] + step_cost
            nodes_generated += 1

            if tentative < g.get(successor, float("inf")):
                g[successor] = tentative
                parent[successor] = (state, edge_ref)
                counter += 1
                h = heuristic(successor)
                heapq.heappush(frontier, (tentative + h, h, counter, successor))

    return finish(
        SearchResult(
            found=False,
            nodes_generated=nodes_generated,
            nodes_expanded=nodes_expanded,
            expansion_order=expansion_order,
            failure_reason="goal is unreachable from the start state",
        )
    )


def _reconstruct(
    goal: S, parent: dict[S, tuple[S, object]]
) -> tuple[list[S], list[object]]:
    """Walk parent links back to the start and reverse."""
    path: list[S] = [goal]
    edges: list[object] = []
    cursor = goal
    while cursor in parent:
        cursor, edge = parent[cursor]
        path.append(cursor)
        edges.append(edge)
    path.reverse()
    edges.reverse()
    return path, edges
