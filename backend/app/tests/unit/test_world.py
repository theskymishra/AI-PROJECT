"""Static world invariants.

The three-corridor property and invariant W1 are load-bearing for later phases.
If either regresses, Phase 4's A* silently misbehaves and the Phase 5 demo
falls flat, so they are asserted here rather than assumed.
"""

import pytest

from app.config import SCALE_KM_PER_UNIT
from app.models.common import ElevationBand, NodeKind
from app.simulation.world import (
    AMBULANCE_SPECS,
    BRIDGE_ROAD_ID,
    CORRIDOR_A,
    CORRIDOR_B,
    CORRIDOR_C,
    HOSPITAL_SPECS,
    build_world,
    geometric_length_km,
)

WORLD = build_world()


def _adjacency():
    adj: dict[str, set[str]] = {}
    for road in WORLD.roads:
        adj.setdefault(road.source, set()).add(road.destination)
        adj.setdefault(road.destination, set()).add(road.source)
    return adj


def _road_between(a: str, b: str):
    for road in WORLD.roads:
        if {road.source, road.destination} == {a, b}:
            return road
    return None


def _path_roads(path):
    roads = []
    for a, b in zip(path, path[1:]):
        road = _road_between(a, b)
        assert road is not None, f"no road between {a} and {b}"
        roads.append(road)
    return roads


# -- size ------------------------------------------------------------------


def test_world_has_the_documented_size():
    assert len(WORLD.nodes) == 24
    assert len(WORLD.roads) == 38
    assert len(WORLD.zones) == 5
    assert len(WORLD.hospitals) == 3
    assert len(WORLD.shelters) == 2
    assert len(WORLD.ambulances) == 4


def test_node_ids_are_unique():
    assert len({n.id for n in WORLD.nodes}) == len(WORLD.nodes)


def test_road_ids_are_unique():
    assert len({r.id for r in WORLD.roads}) == len(WORLD.roads)


def test_no_duplicate_road_between_the_same_pair():
    pairs = [frozenset((r.source, r.destination)) for r in WORLD.roads]
    assert len(set(pairs)) == len(pairs)


def test_no_self_loops():
    assert all(r.source != r.destination for r in WORLD.roads)


def test_every_road_endpoint_is_a_real_node():
    ids = {n.id for n in WORLD.nodes}
    for road in WORLD.roads:
        assert road.source in ids and road.destination in ids


def test_every_node_belongs_to_a_real_zone():
    zone_ids = {z.id for z in WORLD.zones}
    assert all(n.zone_id in zone_ids for n in WORLD.nodes)


# -- invariant W1 ----------------------------------------------------------


def test_invariant_w1_holds_for_every_road():
    """distance >= geometric_length. Without this A* is not admissible."""
    for road in WORLD.roads:
        assert road.distance >= road.geometric_length - 1e-9, (
            f"{road.id}: distance {road.distance} < geometric "
            f"{road.geometric_length}"
        )


def test_distances_are_computed_from_coordinates_not_authored():
    for road in WORLD.roads:
        expected = geometric_length_km(
            WORLD.node_by_id[road.source], WORLD.node_by_id[road.destination]
        )
        assert road.geometric_length == pytest.approx(expected, abs=1e-3)
        assert road.distance == pytest.approx(
            expected * road.detour_factor, abs=1e-3
        )


def test_detour_factors_are_at_least_one():
    assert all(r.detour_factor >= 1.0 for r in WORLD.roads)


def test_distances_are_plausible_for_a_50km_region():
    for road in WORLD.roads:
        assert 1.0 < road.distance < 30.0, f"{road.id} is {road.distance} km"


def test_scale_matches_the_documented_region_size():
    assert 1000 * SCALE_KM_PER_UNIT == pytest.approx(50.0)
    assert 700 * SCALE_KM_PER_UNIT == pytest.approx(35.0)


# -- connectivity ----------------------------------------------------------


def test_graph_is_connected():
    """Union-find, not a graph search.

    Deliberately avoids BFS/DFS: those are on the project's do-not-implement
    list, and while a test oracle would not really violate the spirit of that
    rule, union-find sidesteps the argument entirely.
    """
    parent = {n.id: n.id for n in WORLD.nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for road in WORLD.roads:
        a, b = find(road.source), find(road.destination)
        if a != b:
            parent[a] = b

    assert len({find(n.id) for n in WORLD.nodes}) == 1


def test_every_node_has_at_least_two_roads():
    """A degree-1 node is a dead end that contributes nothing to routing."""
    adj = _adjacency()
    for node in WORLD.nodes:
        assert len(adj.get(node.id, ())) >= 2, f"{node.id} is a dead end"


# -- the three-corridor property -------------------------------------------


@pytest.mark.parametrize(
    "name,path", [("A", CORRIDOR_A), ("B", CORRIDOR_B), ("C", CORRIDOR_C)]
)
def test_each_corridor_is_a_valid_path(name, path):
    roads = _path_roads(path)
    assert len(roads) == len(path) - 1


def test_corridors_share_only_their_endpoints():
    interiors = [set(c[1:-1]) for c in (CORRIDOR_A, CORRIDOR_B, CORRIDOR_C)]
    assert not interiors[0] & interiors[1]
    assert not interiors[0] & interiors[2]
    assert not interiors[1] & interiors[2]


def test_all_corridors_share_the_same_endpoints():
    for corridor in (CORRIDOR_A, CORRIDOR_B, CORRIDOR_C):
        assert corridor[0] == "N1"
        assert corridor[-1] == "N16"


def test_bridge_is_on_corridor_a_only():
    on_a = {r.id for r in _path_roads(CORRIDOR_A)}
    on_bc = {r.id for r in _path_roads(CORRIDOR_B)} | {
        r.id for r in _path_roads(CORRIDOR_C)
    }
    assert BRIDGE_ROAD_ID in on_a
    assert BRIDGE_ROAD_ID not in on_bc


def test_bridge_is_the_only_direct_riverside_to_midtown_link():
    riverside = {n.id for n in WORLD.nodes if n.zone_id == "Z1"}
    midtown = {n.id for n in WORLD.nodes if n.zone_id == "Z2"}
    crossings = [
        r.id
        for r in WORLD.roads
        if {r.source, r.destination} & riverside and {r.source, r.destination} & midtown
    ]
    assert crossings == [BRIDGE_ROAD_ID]


def test_riverside_has_exactly_three_exits():
    riverside = {n.id for n in WORLD.nodes if n.zone_id == "Z1"}
    exits = sorted(
        r.id
        for r in WORLD.roads
        if len({r.source, r.destination} & riverside) == 1
    )
    assert exits == ["R17", "R6", "R7", "R8"], exits


# -- true shortest-path detours -------------------------------------------
#
# Floyd-Warshall: an all-pairs dynamic program, not a graph search, so this
# oracle stays clear of the project's do-not-implement list (BFS, DFS, UCS,
# best-first). It exists only in tests; app/ai/ never imports it.
#
# The earlier version of these tests compared two hand-picked corridors and
# passed while the map had a second Riverside-to-Midtown crossing that reduced
# the real detour to 7%. Comparing against true shortest paths is what caught
# that, so the oracle is worth its twelve lines.

INF = float("inf")


def _shortest_paths(blocked: frozenset[str] = frozenset()):
    ids = [n.id for n in WORLD.nodes]
    index = {node_id: i for i, node_id in enumerate(ids)}
    size = len(ids)
    dist = [[INF] * size for _ in range(size)]
    nxt: list[list[int | None]] = [[None] * size for _ in range(size)]

    for i in range(size):
        dist[i][i] = 0.0

    for road in WORLD.roads:
        if road.id in blocked:
            continue
        i, j = index[road.source], index[road.destination]
        if road.distance < dist[i][j]:
            dist[i][j] = dist[j][i] = road.distance
            nxt[i][j], nxt[j][i] = j, i

    for k in range(size):
        for i in range(size):
            if dist[i][k] == INF:
                continue
            for j in range(size):
                candidate = dist[i][k] + dist[k][j]
                if candidate < dist[i][j]:
                    dist[i][j] = candidate
                    nxt[i][j] = nxt[i][k]
    return dist, nxt, index, ids


def _cost(a: str, b: str, blocked: frozenset[str] = frozenset()) -> float:
    dist, _, index, _ = _shortest_paths(blocked)
    return dist[index[a]][index[b]]


def _path(a: str, b: str, blocked: frozenset[str] = frozenset()) -> list[str]:
    _, nxt, index, ids = _shortest_paths(blocked)
    i, j = index[a], index[b]
    if nxt[i][j] is None:
        return []
    out = [a]
    while i != j:
        step = nxt[i][j]
        assert step is not None
        i = step
        out.append(ids[i])
    return out


def test_blocking_the_bridge_lengthens_the_quay_to_hospital_route():
    """Measured: 33.70 km -> 41.80 km, 1.24x. SEVERE_FLOOD tick 150."""
    open_cost = _cost("N1", "N12")
    blocked_cost = _cost("N1", "N12", frozenset({"R17"}))
    assert open_cost == pytest.approx(33.70, abs=0.1)
    assert blocked_cost == pytest.approx(41.80, abs=0.1)
    assert blocked_cost / open_cost >= 1.15


def _road_ids(path: list[str]) -> list[str]:
    return [_road_between(a, b).id for a, b in zip(path, path[1:])]  # type: ignore[union-attr]


def test_the_replacement_route_is_a_different_route_not_a_nudge():
    """Phase 0: 'a path differing by one node proves nothing'.

    Measured:
        open        N1 -> N2 -> N5 -> N10 -> N11 -> N12   via Midtown
        R17 blocked N1 -> N2 -> N6 -> N9  -> N12          via Old Town

    They share only R1, the first hop out of the Quay, which every route from
    N1 in this direction must take. Everything after it differs: a different
    exit from Riverside, a different zone, a different approach to the
    hospital. Asserting ZERO shared roads would fail on that unavoidable first
    hop, so the assertion is that overlap is confined to it.
    """
    before = _road_ids(_path("N1", "N12"))
    after = _road_ids(_path("N1", "N12", frozenset({"R17"})))
    shared = set(before) & set(after)

    assert len(shared) <= 1, f"routes still share {shared}"
    if shared:
        assert shared == {before[0]}, "overlap is not confined to the first hop"
    assert len(shared) / len(after) <= 0.30


def test_losing_both_southern_exits_forces_a_large_detour():
    """Measured: 42.54 km -> 64.37 km, 1.51x. SEVERE_FLOOD tick 300."""
    open_cost = _cost("N4", "N16")
    blocked_cost = _cost("N4", "N16", frozenset({"R17", "R6"}))
    assert blocked_cost / open_cost >= 1.40, (
        f"detour is only {blocked_cost / open_cost:.2f}x"
    )


def test_riverside_stays_reachable_with_both_southern_exits_closed():
    """No scenario may strand a zone; there is always the northern road."""
    assert _cost("N1", "N16", frozenset({"R17", "R6"})) < INF


def test_every_node_pair_is_reachable_on_an_undamaged_map():
    dist, _, _, ids = _shortest_paths()
    for i in range(len(ids)):
        for j in range(len(ids)):
            assert dist[i][j] < INF, f"{ids[i]} cannot reach {ids[j]}"


def test_corridor_a_is_the_cheapest_of_the_three():
    lengths = {
        name: sum(r.distance for r in _path_roads(path))
        for name, path in (("A", CORRIDOR_A), ("B", CORRIDOR_B), ("C", CORRIDOR_C))
    }
    assert lengths["A"] == min(lengths.values())


# -- facilities ------------------------------------------------------------


def test_facilities_sit_on_facility_nodes():
    facility_nodes = {n.id for n in WORLD.nodes if n.kind is NodeKind.FACILITY}
    for hospital in WORLD.hospitals:
        assert hospital.node_id in facility_nodes
    for shelter in WORLD.shelters:
        assert shelter.node_id in facility_nodes


def test_hospitals_start_at_full_capacity():
    for hospital in WORLD.hospitals:
        assert hospital.available_beds == hospital.total_beds
        assert hospital.available_icu == hospital.total_icu


def test_every_hospital_has_icu_capacity():
    assert all(h.total_icu > 0 for h in WORLD.hospitals)


def test_fleet_capacities_support_the_patients_rule():
    """derive_patients caps at 4; at least one ambulance must be able to take it."""
    from app.models.common import MAX_AMBULANCE_CAPACITY

    capacities = [c for _, _, c, _ in AMBULANCE_SPECS]
    assert max(capacities) == MAX_AMBULANCE_CAPACITY
    # And a real spread, so the capacity constraint prunes rather than passes.
    assert len(set(capacities)) > 1


def test_riverside_hospital_is_in_the_flood_zone():
    """H2 must be exposed, or the hospital-overload story has no cause."""
    h2 = next(h for h in WORLD.hospitals if h.id == "H2")
    assert WORLD.node_by_id[h2.node_id].zone_id == "Z1"
    assert WORLD.zone_by_id["Z1"].elevation_band is ElevationBand.LOW


def test_highland_hospital_is_out_of_it():
    h3 = next(h for h in WORLD.hospitals if h.id == "H3")
    assert WORLD.zone_by_id[
        WORLD.node_by_id[h3.node_id].zone_id
    ].elevation_band is ElevationBand.HIGH


def test_hospital_specs_and_built_hospitals_agree():
    assert len(HOSPITAL_SPECS) == len(WORLD.hospitals)


def test_road_elevation_band_is_the_lower_of_its_two_zones():
    order = {ElevationBand.LOW: 0, ElevationBand.MED: 1, ElevationBand.HIGH: 2}
    for road in WORLD.roads:
        a = WORLD.zone_by_id[WORLD.node_by_id[road.source].zone_id].elevation_band
        b = WORLD.zone_by_id[WORLD.node_by_id[road.destination].zone_id].elevation_band
        assert order[road.elevation_band] == min(order[a], order[b])


def test_build_world_is_pure():
    """Two builds must be identical; the world must not carry run state."""
    first, second = build_world(), build_world()
    assert [r.model_dump() for r in first.roads] == [
        r.model_dump() for r in second.roads
    ]
