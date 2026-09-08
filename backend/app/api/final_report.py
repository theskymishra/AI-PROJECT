"""Phase 14 final system integration API."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.final_report import FinalReportResult
from app.services.final_report_service import final_report_service
from app.simulation.engine import engine

router = APIRouter(tags=["final-report"])


@router.get(
    "/ai/final-report",
    response_model=FinalReportResult,
    summary="Build the final project integration report",
)
def final_report() -> FinalReportResult:
    return final_report_service.build_report(engine.state)
