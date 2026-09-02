"""Frozen Phase 8 planning contracts."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanAction(BaseModel):
    name: str
    args: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    add_effects: list[str] = Field(default_factory=list)
    delete_effects: list[str] = Field(default_factory=list)


class PlanNode(BaseModel):
    task: str
    method: str | None = None
    primitive: bool
    children: list["PlanNode"] = Field(default_factory=list)


class PlanResult(BaseModel):
    status: str
    goal: str
    actions: list[PlanAction] = Field(default_factory=list)
    hierarchy: PlanNode | None = None
    plan_length: int = 0
    nodes_expanded: int = 0
    execution_ms: float = 0.0
    invalidated_step: int | None = None
