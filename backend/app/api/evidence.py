"""Phase 9 Dempster-Shafer evidence fusion endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.evidence import EvidenceRequest, EvidenceResult
from app.services.evidence_service import evidence_service
from app.simulation.engine import engine

router = APIRouter(tags=["ai-evidence"])


@router.post("/ai/evidence", response_model=EvidenceResult, summary="Fuse noisy sensor evidence with Dempster-Shafer theory")
def post_evidence(request: EvidenceRequest = EvidenceRequest()) -> EvidenceResult:
    return evidence_service.analyze(engine.state, request.max_sources)
