"""Phase 13 response evaluation API."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.evaluation import EvaluationResult
from app.services.evaluation_service import evaluation_service
from app.simulation.engine import engine

router = APIRouter(tags=["ai-evaluation"])


@router.get("/ai/evaluation/report", response_model=EvaluationResult, summary="Evaluate current response")
def evaluation_report() -> EvaluationResult:
    return evaluation_service.assess(engine.state, include_plan=True)
