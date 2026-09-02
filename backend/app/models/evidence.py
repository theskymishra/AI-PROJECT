"""Frozen Phase 9 Dempster-Shafer evidence-fusion contracts."""
from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceRequest(BaseModel):
    max_sources: int = Field(default=8, ge=1, le=32)


class EvidenceSource(BaseModel):
    source_id: str
    tick: int = Field(ge=0)
    observation: str
    reliability: float = Field(ge=0.0, le=1.0)
    masses: dict[str, float] = Field(default_factory=dict)


class EvidenceResult(BaseModel):
    status: str
    frame: list[str]
    sources: list[EvidenceSource] = Field(default_factory=list)
    combined_masses: dict[str, float] = Field(default_factory=dict)
    belief: dict[str, float] = Field(default_factory=dict)
    plausibility: dict[str, float] = Field(default_factory=dict)
    pignistic: dict[str, float] = Field(default_factory=dict)
    conflict: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)
    execution_ms: float = Field(ge=0.0)
