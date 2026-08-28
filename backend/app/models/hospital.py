"""Hospital model."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.models.common import HospitalId, HospitalStatus, NodeId

#: Fraction of remaining beds at or below which a hospital is STRAINED.
STRAINED_THRESHOLD = 0.25


class Hospital(BaseModel):
    id: HospitalId
    name: str
    node_id: NodeId
    total_beds: int = Field(ge=0)
    available_beds: int = Field(ge=0)
    total_icu: int = Field(ge=0)
    available_icu: int = Field(ge=0)

    @property
    def status(self) -> HospitalStatus:
        if self.available_beds == 0:
            return HospitalStatus.FULL
        if self.total_beds and self.available_beds / self.total_beds <= STRAINED_THRESHOLD:
            return HospitalStatus.STRAINED
        return HospitalStatus.OPEN

    @property
    def has_icu(self) -> bool:
        return self.total_icu > 0

    @model_validator(mode="after")
    def _check_capacity(self) -> "Hospital":
        if self.available_beds > self.total_beds:
            raise ValueError(
                f"Hospital {self.id}: available_beds ({self.available_beds}) "
                f"exceeds total_beds ({self.total_beds})"
            )
        if self.available_icu > self.total_icu:
            raise ValueError(
                f"Hospital {self.id}: available_icu ({self.available_icu}) "
                f"exceeds total_icu ({self.total_icu})"
            )
        return self
