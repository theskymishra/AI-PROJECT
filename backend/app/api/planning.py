"""Phase 8 hierarchical emergency-response planning endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.planning import PlanResult
from app.services.planning_service import planning_service
from app.simulation.engine import engine

router = APIRouter(tags=["ai-planning"])


@router.post("/ai/plan", response_model=PlanResult, summary="Build a hierarchical emergency-response plan")
def post_plan() -> PlanResult:
    return planning_service.plan(engine.state)
