"""Road-network adapter for the generic A*.

Turns the disaster world into the (successors, goal_test, heuristic) triple the
search expects, and defines the disaster-aware edge cost.

EDGE COST
---------
    w(e) = distance(e) * (1 + ALPHA*flood + BETA*damage + GAMMA*P_fail)

with flood, damage and P_fail all in [0, 1] and the weights non-negative.
Units are RISK-WEIGHTED KILOMETRES: the multiplier is dimensionless, so w(e)
and h(n) share a unit and are directly comparable. That is the detail usually
left vague and then falls apart under questioning.

PHASE NOTE -- READ BEFORE CLAIMING "RISK-AWARE"
-----------------------------------------------
GAMMA multiplies road.failure_probability, which comes from the Bayesian
Network in Phase 5. Until then every road reports 0.0, so the gamma term
contributes nothing and routing is FLOOD- AND DAMAGE-AWARE ONLY. The term is
wired and tested with injected values so that Phase 5 is a data change rather
than a code change, but the honest description of Phase 4 behaviour is
"avoids flooded and damaged roads", not "avoids roads likely to fail".

BLOCKED ROADS
-------------
Excluded from successor generation rather than given an infinite cost. Cleaner
(no infinities propagating through arithmetic) and it keeps the expansion
counts honest -- an unreachable goal reports the nodes actually explored
rather than a frontier stuffed with unusable edges.

ADMISSIBILITY
-------------
    h(n) = SCALE_KM_PER_UNIT * euclid(pos(n), pos(goal))

1. Per edge. flood, damage, P_fail in [0,1] and ALPHA, BETA, GAMMA >= 0, so
   the multiplier M(e) >= 1 and

       w(e) = distance(e) * M(e) >= distance(e) >= geometric_length(e)
            = SCALE * euclid(u, v)

   The middle inequality is WORLD INVARIANT W1, asserted at world-build time.
   Without W1 this proof fails and A* may return a suboptimal path while
   reporting it as optimal.

2. Per path. Summing along any path and applying the triangle inequality:

       sum w(e_i) >= SCALE * sum euclid(n_i, n_i+1) >= SCALE * euclid(n_0, goal)
                  = h(n_0)

   True for every path, hence for the cheapest. So h never overestimates:
   ADMISSIBLE, and h(goal) = 0.

3. Consistency. For any edge (n, n'):

       h(n) = SCALE*euclid(n, goal)
            <= SCALE*euclid(n, n') + SCALE*euclid(n', goal)
            <= w(n, n') + h(n')

   So h is CONSISTENT, which is why the closed-set A* in astar.py is optimal
   without re-opening nodes.

Raising ALPHA, BETA or GAMMA only strengthens step 1, so the weights are free
to tune upward. They may never go negative, and the three road fields must
stay clamped to [0, 1] -- both are enforced by the Road model.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable

from app.ai.search.astar import Successor
from app.config import SCALE_KM_PER_UNIT
from app.models.disaster import Node
from app.models.road import Road


def edge_cost(
    road: Road,
    *,
    alpha: float,
    beta: float,
    gamma: float,
) -> float:
    """Disaster-aware cost of traversing one road, in risk-weighted km."""
    multiplier = (
        1.0
        + alpha * road.flood_level
        + beta * road.damage_level
        + gamma * road.failure_probability
    )
    return road.distance * multiplier


def euclidean_km(a: Node, b: Node) -> float:
    """Straight-line distance between two nodes, in kilometres."""
    return SCALE_KM_PER_UNIT * math.hypot(a.x - b.x, a.y - b.y)


class RoadGraph:
    """Adjacency over the current road network.

    Built per search from live state, because road status changes between
    ticks. Construction is O(roads); at 38 roads that is not worth caching,
    and a stale adjacency would be a far worse bug than a rebuilt one.
    """

    def __init__(
        self,
        nodes: dict[str, Node],
        roads: dict[str, Road],
        *,
        alpha: float,
        beta: float,
        gamma: float,
        avoid: frozenset[str] = frozenset(),
    ) -> None:
        """
        Args:
            nodes: node id -> Node.
            roads: road id -> Road.
            alpha, beta, gamma: cost weights. Must be non-negative.
            avoid: road ids the knowledge engine has derived as Unsafe.
                Phase 6 passes these; they carry a SOFT penalty, unlike
                ``blocked`` which is a hard exclusion. Keeping the two
                distinct is the difference between logic informing routing
                and logic duplicating the blocked flag.
        """
        if min(alpha, beta, gamma) < 0:
            raise ValueError(
                f"cost weights must be non-negative, got "
                f"alpha={alpha} beta={beta} gamma={gamma}; a negative weight "
                f"breaks the admissibility proof in this module's docstring"
            )

        self.nodes = nodes
        self.roads = roads
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.avoid = avoid

        # node id -> list of (neighbour id, road). Roads are bidirectional.
        self._adjacency: dict[str, list[tuple[str, Road]]] = {
            node_id: [] for node_id in nodes
        }
        for road in roads.values():
            if road.source in self._adjacency and road.destination in nodes:
                self._adjacency[road.source].append((road.destination, road))
            if road.destination in self._adjacency and road.source in nodes:
                self._adjacency[road.destination].append((road.source, road))

    def successors(self, node_id: str) -> Iterable[Successor[str]]:
        """Traversable neighbours with their risk-weighted cost."""
        for neighbour, road in self._adjacency.get(node_id, ()):
            if road.blocked:
                continue  # hard exclusion, never traversed
            cost = edge_cost(
                road, alpha=self.alpha, beta=self.beta, gamma=self.gamma
            )
            if road.id in self.avoid:
                # Soft penalty from the knowledge engine. Multiplicative and
                # >= 1, so admissibility is preserved.
                cost *= UNSAFE_PENALTY
            yield neighbour, cost, road.id

    def heuristic_to(self, goal_id: str) -> Callable[[str], float]:
        """Straight-line distance to ``goal_id``, in kilometres."""
        goal = self.nodes[goal_id]
        return lambda node_id: euclidean_km(self.nodes[node_id], goal)

    def degree(self, node_id: str) -> int:
        """Traversable neighbours, ignoring blocked roads."""
        return sum(
            1 for _, road in self._adjacency.get(node_id, ()) if not road.blocked
        )


#: Multiplier applied to roads the knowledge engine has derived as Unsafe.
#: >= 1 so the admissibility proof is unaffected. Unused until Phase 6.
UNSAFE_PENALTY = 2.0
