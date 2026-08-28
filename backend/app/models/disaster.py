"""Static world geometry: nodes and zones."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.common import ElevationBand, NodeId, NodeKind, ZoneId


class Node(BaseModel):
    """A point in the road network: a junction or a facility location."""

    id: NodeId
    name: str
    x: float = Field(ge=0, description="Map coordinate space, 0..1000.")
    y: float = Field(ge=0, description="Map coordinate space, 0..700.")
    zone_id: ZoneId
    kind: NodeKind = NodeKind.JUNCTION


class Zone(BaseModel):
    """A named region of the map."""

    id: ZoneId
    name: str
    polygon: list[tuple[float, float]] = Field(
        min_length=3, description="Closed polygon in map coordinate space."
    )
    population: int = Field(ge=0)
    flood_level: float = Field(default=0.0, ge=0.0, le=1.0)
    elevation: float = Field(
        ge=0.0, le=1.0, description="0 = flood plain, 1 = highland."
    )
    elevation_band: ElevationBand = Field(
        description="Discretised elevation. Roads inherit this for the BN."
    )
