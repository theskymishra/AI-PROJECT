"""The static world.

One fixed map, shared by every scenario. Scenarios differ only in their event
script and initial conditions.

ROAD LENGTHS ARE COMPUTED, NEVER AUTHORED. Each edge declares a detour factor
(>= 1.0, because roads bend); the builder multiplies it by the straight-line
distance between the endpoints. World invariant W1 -- distance >=
geometric_length -- therefore holds by construction rather than by vigilance,
and A*'s heuristic stays admissible in Phase 4.

THE THREE-CORRIDOR PROPERTY
---------------------------
Riverside Quay (N1) reaches Highland Gate (N16) by three routes that share no
node but their endpoints:

  A  bridge      N1 - N5 - N10 - N11 - N14 - N16      via R17, shortest, lowest
  B  north       N1 - N2 - N6  - N9  - N19 - N16      through Old Town
  C  south-east  N1 - N4 - N21 - N23 - N18 - N17 - N16          via R6, longest

R17 (Riverside Bridge) is the ONLY road joining Riverside to Midtown. Riverside
reaches the rest of the region by exactly three roads: R17 (the bridge), R6 (the
southern causeway to Industrial West) and R7/R8 (north into Old Town).

MEASURED DETOURS (test_world.py asserts these; do not restate them from memory)

    Quay N1 -> Central General N12     33.70 km -> 41.80 km   1.24x   on R17 block
    Ferry N4 -> Highland Gate N16      42.54 km -> 64.37 km   1.51x   on R17+R6 block

The SEVERE_FLOOD scenario uses both: emergency E7 appears at the Quay after R17
closes, and E8 appears at Ferry Crossing before R6 closes. Two reroute moments,
each with a fully disjoint replacement path.

This is designed in, not stumbled upon. An earlier draft ran R6 from Ferry
Crossing straight into Midtown South. That gave Riverside a second crossing and
cut the post-blockage detour to about 7% -- a reroute nobody would notice, and
exactly the failure the architecture warns about. Worse, the original test
compared corridor A against corridor B by hand and passed anyway. The test now
computes true shortest-path distances with Floyd-Warshall (an all-pairs DP, not
a graph search, so it stays clear of the project's do-not-implement list), which
is why the flaw surfaced.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.config import SCALE_KM_PER_UNIT
from app.models.ambulance import Ambulance
from app.models.common import ElevationBand, NodeKind
from app.models.disaster import Node, Zone
from app.models.hospital import Hospital
from app.models.road import Road
from app.models.shelter import Shelter

# --------------------------------------------------------------------------
# Zones
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ZoneSpec:
    id: str
    name: str
    polygon: tuple[tuple[float, float], ...]
    population: int
    elevation: float
    band: ElevationBand


ZONE_SPECS: tuple[ZoneSpec, ...] = (
    ZoneSpec(
        "Z1", "Riverside",
        ((40, 400), (340, 400), (340, 700), (40, 700)),
        population=12000, elevation=0.12, band=ElevationBand.LOW,
    ),
    ZoneSpec(
        "Z2", "Midtown",
        ((360, 200), (630, 200), (630, 560), (360, 560)),
        population=18000, elevation=0.50, band=ElevationBand.MED,
    ),
    ZoneSpec(
        "Z3", "Highland",
        ((660, 40), (990, 40), (990, 300), (660, 300)),
        population=6000, elevation=0.88, band=ElevationBand.HIGH,
    ),
    ZoneSpec(
        "Z4", "Industrial",
        ((645, 320), (990, 320), (990, 690), (645, 690)),
        population=4000, elevation=0.28, band=ElevationBand.LOW,
    ),
    ZoneSpec(
        "Z5", "Old Town",
        ((40, 60), (350, 60), (350, 380), (40, 380)),
        population=9000, elevation=0.55, band=ElevationBand.MED,
    ),
)

# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------

# (id, name, x, y, zone, kind)
NODE_SPECS: tuple[tuple[str, str, float, float, str, NodeKind], ...] = (
    ("N1",  "Riverside Quay",    100, 620, "Z1", NodeKind.JUNCTION),
    ("N2",  "Riverside Market",  200, 540, "Z1", NodeKind.JUNCTION),
    ("N3",  "Riverside Clinic",  140, 470, "Z1", NodeKind.FACILITY),
    ("N4",  "Ferry Crossing",    280, 610, "Z1", NodeKind.JUNCTION),
    ("N5",  "Riverside North",   250, 430, "Z1", NodeKind.JUNCTION),
    ("N6",  "Old Town Gate",     150, 300, "Z5", NodeKind.JUNCTION),
    ("N7",  "Cathedral Square",  110, 180, "Z5", NodeKind.JUNCTION),
    ("N8",  "North Depot",       250, 120, "Z5", NodeKind.JUNCTION),
    ("N9",  "Old Mill",          320, 230, "Z5", NodeKind.JUNCTION),
    ("N10", "Midtown West",      390, 400, "Z2", NodeKind.JUNCTION),
    ("N11", "Central Plaza",     500, 330, "Z2", NodeKind.JUNCTION),
    ("N12", "Central General",   470, 250, "Z2", NodeKind.FACILITY),
    ("N13", "Midtown South",     430, 500, "Z2", NodeKind.JUNCTION),
    ("N14", "Midtown East",      600, 380, "Z2", NodeKind.JUNCTION),
    ("N15", "Civic Centre",      560, 470, "Z2", NodeKind.FACILITY),
    ("N16", "Highland Gate",     700, 250, "Z3", NodeKind.JUNCTION),
    ("N17", "Highland Hospital", 820, 160, "Z3", NodeKind.FACILITY),
    ("N18", "Highland School",   900, 240, "Z3", NodeKind.FACILITY),
    ("N19", "Ridge Junction",    760,  90, "Z3", NodeKind.JUNCTION),
    ("N20", "Highland East",     940, 120, "Z3", NodeKind.JUNCTION),
    ("N21", "Industrial West",   680, 470, "Z4", NodeKind.JUNCTION),
    ("N22", "Port Terminal",     780, 600, "Z4", NodeKind.JUNCTION),
    ("N23", "Freight Yard",      900, 500, "Z4", NodeKind.JUNCTION),
    ("N24", "Industrial East",   960, 620, "Z4", NodeKind.JUNCTION),
)

# --------------------------------------------------------------------------
# Roads
# --------------------------------------------------------------------------

# (id, source, destination, detour_factor)
ROAD_SPECS: tuple[tuple[str, str, str, float], ...] = (
    # Riverside internal
    ("R1",  "N1",  "N2",  1.15),
    ("R2",  "N1",  "N4",  1.10),
    ("R3",  "N2",  "N3",  1.10),
    ("R4",  "N2",  "N5",  1.15),
    ("R5",  "N3",  "N5",  1.05),
    # Riverside exits. These three roads are the whole of Riverside's
    # connection to the rest of the region.
    ("R6",  "N4",  "N21", 1.25),   # Southern Causeway, corridor C
    ("R7",  "N2",  "N6",  1.20),   # north, corridor B
    ("R8",  "N3",  "N6",  1.15),
    # Old Town internal
    ("R9",  "N6",  "N7",  1.10),
    ("R10", "N7",  "N8",  1.15),
    ("R11", "N8",  "N9",  1.10),
    ("R12", "N6",  "N9",  1.20),
    # Old Town outward
    ("R13", "N9",  "N12", 1.15),
    ("R14", "N9",  "N19", 1.10),   # North Ridge Road, corridor B
    ("R15", "N6",  "N10", 1.20),
    ("R16", "N10", "N11", 1.10),
    # THE BRIDGE. The only road joining Riverside to Midtown.
    ("R17", "N5",  "N10", 1.05),   # Riverside Bridge
    ("R18", "N10", "N13", 1.15),
    # Midtown internal
    ("R19", "N11", "N12", 1.10),
    ("R20", "N11", "N13", 1.20),
    ("R21", "N11", "N14", 1.10),
    ("R22", "N13", "N15", 1.15),
    ("R23", "N14", "N15", 1.20),
    # Midtown to Highland
    ("R24", "N12", "N16", 1.10),
    ("R25", "N14", "N16", 1.15),
    # Midtown to Industrial
    ("R26", "N14", "N21", 1.10),
    ("R27", "N15", "N21", 1.15),
    # Highland internal
    ("R28", "N16", "N17", 1.10),
    ("R29", "N16", "N19", 1.15),
    ("R30", "N17", "N18", 1.15),
    ("R31", "N18", "N20", 1.15),
    ("R32", "N19", "N20", 1.10),
    ("R33", "N18", "N23", 1.10),   # corridor C link
    # Industrial internal
    ("R34", "N21", "N22", 1.20),
    ("R35", "N21", "N23", 1.15),
    ("R36", "N22", "N24", 1.20),
    ("R37", "N23", "N24", 1.15),
    # Riverside internal, direct quay link
    ("R38", "N1",  "N5",  1.20),
)

#: The road whose removal destroys corridor A. Named because the scenario
#: scripts, the tests and the demo script all refer to it.
BRIDGE_ROAD_ID = "R17"

#: Asserted by tests/unit/test_world.py.
CORRIDOR_A = ("N1", "N5", "N10", "N11", "N14", "N16")
CORRIDOR_B = ("N1", "N2", "N6", "N9", "N19", "N16")
CORRIDOR_C = ("N1", "N4", "N21", "N23", "N18", "N17", "N16")

# --------------------------------------------------------------------------
# Facilities and fleet
# --------------------------------------------------------------------------

# (id, name, node, total_beds, total_icu)
HOSPITAL_SPECS: tuple[tuple[str, str, str, int, int], ...] = (
    ("H1", "Central General",   "N12", 48, 8),
    ("H2", "Riverside Clinic",  "N3",  24, 4),   # floods first
    ("H3", "Highland Hospital", "N17", 36, 6),   # safe but far
)

# (id, name, node, capacity, safety_score)
SHELTER_SPECS: tuple[tuple[str, str, str, int, float], ...] = (
    ("S1", "Highland School", "N18", 400, 0.95),
    ("S2", "Civic Centre",    "N15", 250, 0.70),
)

# (id, node, capacity, speed_kmh)
#
# Capacities 2/2/4/4. A 3-patient emergency eliminates A1 and A2 outright,
# which is the domain reduction the Phase 7 CSP needs in order to produce
# non-zero backtrack and propagation counters.
AMBULANCE_SPECS: tuple[tuple[str, str, int, float], ...] = (
    ("A1", "N2",  2, 55.0),
    ("A2", "N11", 2, 60.0),
    ("A3", "N12", 4, 60.0),
    ("A4", "N16", 4, 65.0),
)

# (id, zone, is_river_gauge)
#
# SEN6 is the river gauge. Phase 5's HMM consumes its observation stream; the
# others feed per-zone display and, later, Bayesian evidence.
SENSOR_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("SEN1", "Z1", False),
    ("SEN2", "Z2", False),
    ("SEN3", "Z3", False),
    ("SEN4", "Z4", False),
    ("SEN5", "Z5", False),
    ("SEN6", "Z1", True),
)

PRIMARY_SENSOR_ID = "SEN6"

# --------------------------------------------------------------------------
# Builder
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class World:
    """Immutable static geometry. Mutable per-run state lives in WorldState."""

    zones: tuple[Zone, ...]
    nodes: tuple[Node, ...]
    roads: tuple[Road, ...]
    hospitals: tuple[Hospital, ...]
    shelters: tuple[Shelter, ...]
    ambulances: tuple[Ambulance, ...]
    node_by_id: dict[str, Node]
    zone_by_id: dict[str, Zone]
    road_by_id: dict[str, Road]

    def roads_touching_zone(self, zone_id: str) -> list[Road]:
        return [
            road
            for road in self.roads
            if self.node_by_id[road.source].zone_id == zone_id
            or self.node_by_id[road.destination].zone_id == zone_id
        ]


def euclid_units(a: Node, b: Node) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def geometric_length_km(a: Node, b: Node) -> float:
    """Straight-line distance in kilometres. The floor for invariant W1."""
    return euclid_units(a, b) * SCALE_KM_PER_UNIT


def _lower_band(a: ElevationBand, b: ElevationBand) -> ElevationBand:
    """A road is only as safe as its lowest point."""
    order = {ElevationBand.LOW: 0, ElevationBand.MED: 1, ElevationBand.HIGH: 2}
    return a if order[a] <= order[b] else b


def build_world() -> World:
    """Construct the static world. Pure; no randomness, no clock."""
    zones = tuple(
        Zone(
            id=spec.id,
            name=spec.name,
            polygon=[(x, y) for x, y in spec.polygon],
            population=spec.population,
            flood_level=0.0,
            elevation=spec.elevation,
            elevation_band=spec.band,
        )
        for spec in ZONE_SPECS
    )
    zone_by_id = {zone.id: zone for zone in zones}

    nodes = tuple(
        Node(id=nid, name=name, x=x, y=y, zone_id=zone_id, kind=kind)
        for nid, name, x, y, zone_id, kind in NODE_SPECS
    )
    node_by_id = {node.id: node for node in nodes}

    roads: list[Road] = []
    for rid, source, destination, detour in ROAD_SPECS:
        a, b = node_by_id[source], node_by_id[destination]
        geometric = geometric_length_km(a, b)
        roads.append(
            Road(
                id=rid,
                source=source,
                destination=destination,
                # Computed, never authored. This is what makes W1 hold.
                distance=round(geometric * detour, 4),
                geometric_length=round(geometric, 4),
                detour_factor=detour,
                elevation_band=_lower_band(
                    zone_by_id[a.zone_id].elevation_band,
                    zone_by_id[b.zone_id].elevation_band,
                ),
            )
        )
    roads_t = tuple(roads)

    hospitals = tuple(
        Hospital(
            id=hid, name=name, node_id=node_id,
            total_beds=beds, available_beds=beds,
            total_icu=icu, available_icu=icu,
        )
        for hid, name, node_id, beds, icu in HOSPITAL_SPECS
    )

    shelters = tuple(
        Shelter(
            id=sid, name=name, node_id=node_id,
            capacity=capacity, occupancy=0, safety_score=safety,
        )
        for sid, name, node_id, capacity, safety in SHELTER_SPECS
    )

    ambulances = tuple(
        Ambulance(id=aid, node_id=node_id, capacity=capacity, speed_kmh=speed)
        for aid, node_id, capacity, speed in AMBULANCE_SPECS
    )

    return World(
        zones=zones,
        nodes=nodes,
        roads=roads_t,
        hospitals=hospitals,
        shelters=shelters,
        ambulances=ambulances,
        node_by_id=node_by_id,
        zone_by_id=zone_by_id,
        road_by_id={road.id: road for road in roads_t},
    )
