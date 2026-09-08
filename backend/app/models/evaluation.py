"""Phase 13 response evaluation and scenario analytics contracts."""
from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationMetric(BaseModel):
    name: str
    value: float = Field(default=0.0, ge=0)
    unit: str
    interpretation: str


class EvaluationResult(BaseModel):
    status: str
    tick: int = Field(default=0, ge=0)
    scenario: str
    summary: str
    readiness: str
    metrics: list[EvaluationMetric] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    active_emergencies: int = Field(default=0, ge=0)
    resolved_emergencies: int = Field(default=0, ge=0)
    unresolvable_emergencies: int = Field(default=0, ge=0)
    assigned_emergencies: int = Field(default=0, ge=0)
    unassigned_emergencies: int = Field(default=0, ge=0)
    ambulances_available: int = Field(default=0, ge=0)
    ambulances_total: int = Field(default=0, ge=0)
    beds_available: int = Field(default=0, ge=0)
    beds_total: int = Field(default=0, ge=0)
    audit_events: int = Field(default=0, ge=0)
    plan_status: str = "NOT_REQUESTED"
    plan_length: int = Field(default=0, ge=0)
