"""Phase 10 plan-execution contracts."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.planning import PlanAction


class ExecutionResult(BaseModel):
    """Current execution state plus the plan being executed."""

    status: str
    message: str
    plan: list[PlanAction] = Field(default_factory=list)
    next_action_index: int | None = None
    executed_count: int = Field(default=0, ge=0)
    total_actions: int = Field(default=0, ge=0)
    last_action: PlanAction | None = None
    tick: int = Field(default=0, ge=0)
    snapshot: dict = Field(default_factory=dict)
