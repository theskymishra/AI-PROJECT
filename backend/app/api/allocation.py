"""Phase 7 CSP resource-allocation endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models.ai_result import CSPResult
from app.services.csp_service import csp_allocator
from app.simulation.engine import engine

router = APIRouter(tags=["ai-allocation"])

class AllocationRequest(BaseModel):
    apply: bool = Field(default=False, description="Preview by default; set true to commit assignments.")

@router.post("/ai/allocate", response_model=CSPResult, summary="Solve or apply Phase 7 emergency resource allocation")
def post_allocate(request: AllocationRequest) -> CSPResult:
    result = csp_allocator.solve(engine.state)
    if request.apply and result.assignments:
        result = csp_allocator.apply(engine.state, result)
    return result
