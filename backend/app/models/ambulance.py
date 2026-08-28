"""Ambulance model."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.common import (
    AmbulanceId,
    AmbulanceStatus,
    EmergencyId,
    NodeId,
    RoadId,
)


class EdgePosition(BaseModel):
    """Position of a vehicle part-way along a road, for map animation."""

    road_id: RoadId
    progress: float = Field(ge=0.0, le=1.0, description="0 at source, 1 at destination.")


class Ambulance(BaseModel):
    id: AmbulanceId
    node_id: NodeId = Field(description="Nearest node; the source of A* queries.")
    position: EdgePosition | None = Field(
        default=None, description="Set only while travelling between nodes."
    )
    capacity: int = Field(ge=1, description="Maximum patients carried in one trip.")
    speed_kmh: float = Field(gt=0)
    status: AmbulanceStatus = AmbulanceStatus.AVAILABLE
    assigned_emergency: EmergencyId | None = None
