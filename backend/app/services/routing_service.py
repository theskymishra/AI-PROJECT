"""Routing service: A* over live world state, plus the route cache.

THE CACHE
---------
    key = (start_node_id, goal_node_id, environment_version, avoid_roads)

``environment_version`` is monotonic and lives on WorldState. An entry whose
key does not match the CURRENT version can never be read, so a stale route is
unreachable by construction rather than by remembering to evict. That is the
whole design: correctness first, at a world size where the recompute cost does
not register.

WHY THE CACHE EXISTS AT ALL
---------------------------
It was moved forward from Phase 7 because Phase 5's hard-failure demo needs it:
blocking a road must invalidate the committed route and force a genuinely
different one. It also breaks the CSP <-> A* dependency cycle in Phase 7 --
"destination must be reachable" is a CSP constraint that requires a path
search, so the allocator consults this cache instead of calling A* from inside
constraint checking.

DELIBERATE TRADE-OFF
--------------------
One global version invalidates EVERY cached route when ANY road changes,
including routes that never touched it. Per-road dependency tracking would be
tighter. At 38 roads and a few dozen queries per solve the full recompute is
sub-millisecond, so this buys correctness-by-construction for a cost that does
not show up. Revisit if the graph grows an order of magnitude.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.search.astar import astar
from app.ai.search.road_graph import RoadGraph
from app.config import (
    COST_WEIGHT_DAMAGE,
    COST_WEIGHT_FAILURE,
    COST_WEIGHT_FLOOD,
)
from app.models.ai_result import RouteResult
from app.simulation.state import WorldState

#: (start, goal, environment_version)
CacheKey = tuple[str, str, int, tuple[str, ...]]


@dataclass
class CacheStats:
    """Observable cache behaviour, surfaced through the API.

    Exposed because "the cache is working" is otherwise an article of faith.
    A hit rate stuck at zero means the invalidation rule is too eager -- which
    is exactly the bug RISK_EPSILON was introduced to prevent.
    """

    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    entries: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return 0.0 if total == 0 else self.hits / total


class RoutingService:
    """Computes and caches disaster-aware routes."""

    def __init__(
        self,
        *,
        alpha: float = COST_WEIGHT_FLOOD,
        beta: float = COST_WEIGHT_DAMAGE,
        gamma: float = COST_WEIGHT_FAILURE,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self._cache: dict[CacheKey, RouteResult] = {}
        self._cached_version: int | None = None
        self.stats = CacheStats()

    # -- cache -------------------------------------------------------------

    def _purge_if_stale(self, version: int) -> None:
        """Drop everything when the environment moves on.

        Entries keyed on an older version could never be read anyway; purging
        keeps the dict from growing without bound over a long run.
        """
        if self._cached_version is not None and self._cached_version != version:
            self._cache.clear()
            self.stats.invalidations += 1
        self._cached_version = version
        self.stats.entries = len(self._cache)

    def clear_cache(self) -> None:
        self._cache.clear()
        self._cached_version = None
        self.stats = CacheStats()

    # -- routing -----------------------------------------------------------

    def graph_for(
        self, state: WorldState, avoid: frozenset[str] = frozenset()
    ) -> RoadGraph:
        return RoadGraph(
            nodes=state.world.node_by_id,
            roads=state.roads,
            alpha=self.alpha,
            beta=self.beta,
            gamma=self.gamma,
            avoid=avoid,
        )

    def route(
        self,
        state: WorldState,
        start: str,
        goal: str,
        *,
        avoid: frozenset[str] = frozenset(),
        use_cache: bool = True,
    ) -> RouteResult:
        """Cheapest disaster-aware route from ``start`` to ``goal``.

        Raises:
            KeyError: If either node id is not in the world. Callers at the
                API boundary turn this into a 404 rather than letting it
                surface as a 500.
        """
        # Nodes are static geometry and live on World; only roads mutate
        # per tick and live on WorldState. Reading nodes from state.world
        # keeps that separation explicit rather than duplicating the node
        # table into every snapshot.
        nodes = state.world.node_by_id
        if start not in nodes:
            raise KeyError(f"unknown start node {start!r}")
        if goal not in nodes:
            raise KeyError(f"unknown goal node {goal!r}")

        version = state.environment_version
        self._purge_if_stale(version)

        # Phase 6 makes symbolic Avoid(R) part of the routing decision. Include
        # it in the cache key so two logically different searches can never
        # share a result. The avoid set is derived from road state, and any
        # relevant road-state change already advances environment_version.
        cacheable = use_cache
        key: CacheKey = (start, goal, version, tuple(sorted(avoid)))

        if cacheable and key in self._cache:
            self.stats.hits += 1
            return self._cache[key]

        if cacheable:
            self.stats.misses += 1

        result = self._search(state, start, goal, avoid=avoid, version=version)

        if cacheable:
            self._cache[key] = result
            self.stats.entries = len(self._cache)

        return result

    def _search(
        self,
        state: WorldState,
        start: str,
        goal: str,
        *,
        avoid: frozenset[str],
        version: int,
    ) -> RouteResult:
        graph = self.graph_for(state, avoid=avoid)

        search = astar(
            start=start,
            successors=graph.successors,
            goal_test=lambda node_id: node_id == goal,
            heuristic=graph.heuristic_to(goal),
        )

        if not search.found:
            return RouteResult(
                found=False,
                environment_version=version,
                nodes_generated=search.nodes_generated,
                nodes_expanded=search.nodes_expanded,
                execution_ms=search.execution_ms,
                expansion_order=list(search.expansion_order),
                failure_reason=self._explain_failure(state, start, goal, graph),
            )

        edges = [str(edge) for edge in search.edges]
        # Plain kilometres alongside risk-weighted cost. Showing both is what
        # makes "the safer route is longer" legible instead of a bare number.
        total_distance = sum(state.roads[rid].distance for rid in edges)

        return RouteResult(
            found=True,
            path=list(search.path),
            edges=edges,
            total_cost=round(search.total_cost, 4),
            total_distance=round(total_distance, 4),
            nodes_generated=search.nodes_generated,
            nodes_expanded=search.nodes_expanded,
            execution_ms=search.execution_ms,
            expansion_order=list(search.expansion_order),
            environment_version=version,
        )

    @staticmethod
    def _explain_failure(
        state: WorldState, start: str, goal: str, graph: RoadGraph
    ) -> str:
        """Say WHY there is no route, not merely that there isn't one.

        'No route found' sends an operator hunting through the map. Naming the
        isolated endpoint points straight at the cause.
        """
        if start == goal:
            return "start and goal are the same node"
        if graph.degree(start) == 0:
            name = state.world.node_by_id[start].name
            return f"every road out of {name} ({start}) is blocked"
        if graph.degree(goal) == 0:
            name = state.world.node_by_id[goal].name
            return f"every road into {name} ({goal}) is blocked"
        return (
            f"no open route from {start} to {goal}; blocked roads have "
            f"separated them into disconnected parts of the network"
        )


#: Process-wide instance, mirroring the single-worker simulation engine.
routing_service = RoutingService()
