"""Phase 11 response monitoring contracts."""
from __future__ import annotations

from pydantic import BaseModel, Field


class MonitoringItem(BaseModel):
    emergency_id: str
    status: str
    ambulance_id: str | None = None
    hospital_id: str | None = None
    severity: str | None = None
    patients: int = Field(default=0, ge=0)
    route_ready: bool = True
    attention: str
    recommendation: str


class ResourceHealth(BaseModel):
    ambulances_available: int = Field(default=0, ge=0)
    ambulances_total: int = Field(default=0, ge=0)
    beds_available: int = Field(default=0, ge=0)
    beds_total: int = Field(default=0, ge=0)
    active_emergencies: int = Field(default=0, ge=0)
    assigned_emergencies: int = Field(default=0, ge=0)


class MonitoringResult(BaseModel):
    status: str
    tick: int = Field(default=0, ge=0)
    overall: str
    summary: str
    health: ResourceHealth
    items: list[MonitoringItem] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    replanning_required: bool = False
    plan_length: int = Field(default=0, ge=0)
    plan_status: str = "NOT_REQUESTED"
