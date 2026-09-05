"""Phase 11 response monitoring API."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.monitoring import MonitoringResult
from app.services.monitoring_service import monitoring_service
from app.simulation.engine import engine

router = APIRouter(tags=["ai-monitoring"])


@router.get("/ai/monitoring/status", response_model=MonitoringResult, summary="Assess live response health")
def monitoring_status() -> MonitoringResult:
    return monitoring_service.assess(engine.state, include_plan=False)


@router.post("/ai/monitoring/replan-check", response_model=MonitoringResult, summary="Assess state and current HTN replanning readiness")
def replan_check() -> MonitoringResult:
    return monitoring_service.assess(engine.state, include_plan=True)
