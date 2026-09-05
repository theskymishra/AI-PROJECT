"""Phase 12 decision explainability and audit contracts."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DecisionStep(BaseModel):
    component: str
    decision: str
    rationale: str
    evidence: list[str] = Field(default_factory=list)


class EmergencyExplanation(BaseModel):
    emergency_id: str
    status: str
    severity: str | None = None
    patients: int = Field(default=0, ge=0)
    ambulance_id: str | None = None
    hospital_id: str | None = None
    decision: str
    rationale: str
    steps: list[DecisionStep] = Field(default_factory=list)


class ExplainabilityResult(BaseModel):
    status: str
    tick: int = Field(default=0, ge=0)
    summary: str
    ai_chain: list[str] = Field(default_factory=list)
    explanations: list[EmergencyExplanation] = Field(default_factory=list)
    audit_events: int = Field(default=0, ge=0)
    plan_status: str = "NOT_REQUESTED"
    plan_length: int = Field(default=0, ge=0)
