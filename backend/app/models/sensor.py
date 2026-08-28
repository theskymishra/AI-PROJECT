"""Sensor reading model.

The observation symbol is emitted with noise from the true hidden flood state
(Phase 0 section 7.2). It is NOT a deterministic function of water_level_m --
that is what gives the HMM real work to do.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.common import Observation, SensorId, ZoneId


class SensorReading(BaseModel):
    tick: int = Field(ge=0)
    sensor_id: SensorId
    zone_id: ZoneId
    rainfall_mm: float = Field(ge=0)
    water_level_m: float = Field(ge=0)
    river_level_m: float = Field(ge=0)
    observation: Observation = Field(
        description="Discretised, noisily emitted. Input to the HMM forward algorithm."
    )
