"""Shelter model."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.models.common import NodeId, ShelterId, ShelterStatus

#: Occupancy fraction at or above which a shelter is NEAR_FULL.
NEAR_FULL_THRESHOLD = 0.85


class Shelter(BaseModel):
    id: ShelterId
    name: str
    node_id: NodeId
    capacity: int = Field(ge=0)
    occupancy: int = Field(default=0, ge=0)
    safety_score: float = Field(ge=0.0, le=1.0)

    @property
    def status(self) -> ShelterStatus:
        if self.capacity == 0 or self.occupancy >= self.capacity:
            return ShelterStatus.FULL
        if self.occupancy / self.capacity >= NEAR_FULL_THRESHOLD:
            return ShelterStatus.NEAR_FULL
        return ShelterStatus.OPEN

    @model_validator(mode="after")
    def _check_occupancy(self) -> "Shelter":
        if self.occupancy > self.capacity:
            raise ValueError(
                f"Shelter {self.id}: occupancy ({self.occupancy}) exceeds "
                f"capacity ({self.capacity})"
            )
        return self
