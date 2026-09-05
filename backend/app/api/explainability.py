"""Phase 12 decision explainability API."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.explainability import ExplainabilityResult
from app.services.explainability_service import explainability_service
from app.simulation.engine import engine

router = APIRouter(tags=["ai-explainability"])


@router.get("/ai/explainability/report", response_model=ExplainabilityResult, summary="Explain current AI decisions")
def explainability_report() -> ExplainabilityResult:
    return explainability_service.build_report(engine.state, include_plan=True)
