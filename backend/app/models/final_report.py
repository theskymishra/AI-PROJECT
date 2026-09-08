"""Phase 14 final system integration and project summary contracts."""
from __future__ import annotations

from pydantic import BaseModel, Field


class FinalSubsystem(BaseModel):
    phase: int = Field(ge=1)
    name: str
    purpose: str
    status: str
    evidence: str


class FinalReportResult(BaseModel):
    """Read-only final integration report assembled from live project layers."""

    status: str
    project: str
    version: str
    phase: int = Field(ge=1)
    total_phases: int = Field(ge=1)
    tick: int = Field(default=0, ge=0)
    scenario: str
    simulation_status: str
    environment_version: int = Field(default=0, ge=0)

    zones: int = Field(default=0, ge=0)
    roads: int = Field(default=0, ge=0)
    hospitals: int = Field(default=0, ge=0)
    shelters: int = Field(default=0, ge=0)
    ambulances: int = Field(default=0, ge=0)
    emergencies: int = Field(default=0, ge=0)
    sensor_readings: int = Field(default=0, ge=0)
    timeline_events: int = Field(default=0, ge=0)

    monitoring_status: str
    readiness: str
    replanning_required: bool
    explainability_audit_events: int = Field(default=0, ge=0)
    evaluation_plan_status: str
    evaluation_plan_length: int = Field(default=0, ge=0)

    summary: str
    subsystems: list[FinalSubsystem] = Field(default_factory=list)
    final_checks: list[str] = Field(default_factory=list)
